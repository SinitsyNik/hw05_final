import shutil
import tempfile

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from posts.views import POSTS_COUNT

from ..models import Group, Post, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='popo')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-description',
        )
        cls.new_group = Group.objects.create(
            title='new test-title',
            slug='new-test-slug',
            description='new test-description',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test-text',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def context_on_page(self, context_objects):
        self.assertEqual(context_objects.author, self.post.author)
        self.assertEqual(context_objects.text, self.post.text)
        self.assertEqual(context_objects.group, self.post.group)
        self.assertEqual(context_objects.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        index_post = response.context['page_obj'][0]
        self.context_on_page(index_post)

    def test_group_list_pages_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        )
        response_group = response.context.get('group')
        group_post = response.context['page_obj'][0]
        self.context_on_page(group_post)
        self.assertEqual(group_post.author, self.user)
        self.assertEqual(response_group.title, self.group.title)
        self.assertEqual(response_group.slug, self.group.slug)
        self.assertEqual(response_group.description, self.group.description)

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        )
        response_profile = response.context.get('post_count')
        profile_post = response.context['page_obj'][0]
        self.context_on_page(profile_post)
        self.assertEqual(response_profile, 1)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        )
        response_post = response.context.get('post')
        response_total_posts_user = response.context.get('total_posts_user')
        self.context_on_page(response_post)
        self.assertEqual(response_total_posts_user, 1)
        self.assertEqual(self.post, response_post)

    def test_post_create_and_post_edit_show_correct_context(self):
        """Шаблоны post_create и post_edit сформирован
        с правильным контекстом.
        """
        pages_names = {
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            reverse('posts:post_create')
        }
        for url in pages_names:
            response = self.authorized_client.get(url)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.models.ModelChoiceField,
                'image': forms.fields.ImageField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_post_group_appears_on_page(self):
        """Проверка нового поста при указании группы на страницах
         index, group_list и profile.
        """
        pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        }
        for url in pages_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']), 1)
                self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_not_appers_in_another_group(self):
        """"Проверяем, что пост не попал в группу,
        для которой не был предназначен.
        """
        new_group_url = reverse('posts:group_list',
                                kwargs={'slug': self.new_group.slug})
        response = self.authorized_client.get(new_group_url)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_index_page_cache(self):
        """Проверка кеширования главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        cache_content = response.content
        Post.objects.all().delete()
        response = self.authorized_client.get(reverse('posts:index'))
        cache_content_delete = response.content
        self.assertEqual(cache_content, cache_content_delete)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        cache_content_clear = response.content
        self.assertNotEqual(cache_content, cache_content_clear)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='popo')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-description',
        )
        cls.post = [
            Post.objects.create(
                author=cls.user,
                text='test-text' + str(i),
                group=cls.group
            )
            for i in range(13)]

    def test_index_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), POSTS_COUNT)

    def test_index_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        second_page = Post.objects.count() % POSTS_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)

    def test_group_list_first_page_contains_ten_records(self):
        response = self.client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), POSTS_COUNT)

    def test_group_list_second_page_contains_three_records(self):
        response = self.client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
            + '?page=2'
        )
        second_page = Post.objects.count() % POSTS_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)

    def test_profile_first_page_contains_ten_records(self):
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(len(response.context['page_obj']), POSTS_COUNT)

    def test_profile_second_page_contains_three_records(self):
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username})
            + '?page=2'
        )
        second_page = Post.objects.count() % POSTS_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)


class FollowsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='popo')
        cls.user_2 = User.objects.create_user(username='lopo')
        cls.post = Post.objects.create(
            author=cls.user_2,
            text='test-text'
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_1)

    def test_authorized_user_can_follow_other_users(self):
        """Авторизованный пользователь может подписываться
        на других пользователей.
        """
        follow_count = Follow.objects.count()
        self.assertFalse(Follow.objects.filter(
            user=self.user_1,
            author=self.user_2).exists())
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(Follow.objects.filter(
            user=self.user_1,
            author=self.user_2).exists())

    def test_authorized_user_can_unfollow_other_users(self):
        """Авторизованный пользователь может отписываться
        от других пользователей.
        """
        Follow.objects.create(
            user=self.user_1,
            author=self.user_2)
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(Follow.objects.filter(
            user=self.user_1,
            author=self.user_2).exists())

    def test_new_post_appears_in_the_page_followers(self):
        """Новая запись пользователя появляется в ленте подписчиков."""
        Follow.objects.create(
            user=self.user_1,
            author=self.user_2)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_context = response.context['page_obj']
        self.assertIn(self.post, follow_context)

    def test_new_post_does_not_appears_in_the_page_not_followers(self):
        """Новая запись пользователя не появляется в ленте
        у тех, кто не подписан.
        """
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_context = response.context['page_obj']
        self.assertNotIn(self.post, follow_context)
