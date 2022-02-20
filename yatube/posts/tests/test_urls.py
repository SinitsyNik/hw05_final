from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='popo')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_guest_urls(self):
        """Страницы доступные любому пользователю."""
        templates_url_names = {
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.pk}/',
        }
        for address in templates_url_names:
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_urls(self):
        """Страницы доступные авторизованному пользователю."""
        templates_url_names = {
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.pk}/',
            '/create/',
        }
        for address in templates_url_names:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author_post_urls(self):
        """Страницы доступные автору."""
        templates_url_names = {
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.pk}/',
            '/create/',
            f'/posts/{self.post.pk}/edit/',
        }
        for address in templates_url_names:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_post_create_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_post_edit_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /posts/1/edit/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.client.get(f'/posts/{self.post.pk}/edit/', follow=True)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        )

    def test_server_responds_404_for_unexisted_page(self):
        """Несуществующая странице вернёт ошибку 404"""
        response = self.client.get('/unexisted-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
