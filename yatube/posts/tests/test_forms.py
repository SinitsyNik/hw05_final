import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='popo')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_save(self):
        """Валидная форма создает запись в базе данных
        на странице create и перенаправляет на страницу profile.
        """
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
            content_type='image/gif'
        )
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст из формы',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username})
        )
        post = Post.objects.order_by('id').last()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertTrue(post.image, form_data['image'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_save(self):
        """Валидная форма сохраняет записьв базе данных
        на странице post_edit и перенаправляет на страницу post_detail.
        """
        post = Post.objects.create(
            author=self.user,
            text='test-text',
            group=self.group,
        )
        form_data = {
            'text': 'Новый текст формы',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': post.id})
        )
        edit_post = Post.objects.get(id=post.id)
        self.assertEqual(edit_post.text, form_data['text'])
        self.assertEqual(edit_post.group.id, form_data['group'])
        self.assertEqual(response.status_code, HTTPStatus.OK)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='popo')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test-text',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_only_authorized_client_can_comment_posts(self):
        '''Комментировать посты может только авторизованный пользователь.'''
        comment_count = self.post.comments.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(self.post.comments.count(), comment_count + 1)
        self.assertEqual(self.post.comments.last().text, form_data['text'])
