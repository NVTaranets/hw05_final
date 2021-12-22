# posts/tests/test_urls.py
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()

GUEST_ROLE = 'Guest'
AUTORIZED_ROLE = 'HasNoName'
AUTHOR_ROLE = 'Author'


class TaskURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_name = (
            GUEST_ROLE,
            AUTORIZED_ROLE,
            AUTHOR_ROLE,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.users = dict()
        for user in cls.user_name:
            if user != GUEST_ROLE:
                cls.users[user] = User.objects.create_user(username=user)
        cls.post_user = Post.objects.create(
            author=cls.users[AUTORIZED_ROLE],
            text='Тестовый пост с длинным текстом',
        )
        cls.post_author = Post.objects.create(
            author=cls.users[AUTHOR_ROLE],
            text='Тестовый пост с длинным текстом',
        )
        cls.clients = {key: val for key, val
                       in zip(cls.user_name, (Client(), Client(), Client()))}
        cls.clients[AUTORIZED_ROLE].force_login(cls.users[AUTORIZED_ROLE])
        cls.clients[AUTHOR_ROLE].force_login(cls.users[AUTHOR_ROLE])
        post_id = str(cls.post_author.pk)
        url_group = reverse(
            'posts:group_list',
            kwargs={'slug': cls.group.slug}
        )
        url_profile = reverse(
            'posts:profile',
            kwargs={'username': cls.post_author.author}
        )
        url_login = reverse('login')
        url_post = reverse('posts:post_detail', kwargs={'post_id': post_id})
        url_edit = reverse('posts:post_edit', kwargs={'post_id': post_id})
        url_create = reverse('posts:post_create')
        url_comment = reverse('posts:add_comment', kwargs={'post_id': post_id})
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': cls.post_author.author}
        )
        url_unfollow = reverse(
            'posts:profile_unfollow',
            kwargs={'username': cls.post_author.author}
        )
        # словарь исходных данных для тестов
        # ключ содержит url и имя пользователя
        # значение это список из 2 элементов:
        # шаблона, [и адреса редиректа (если он есть)]
        cls.dict_tests = {
            f'/:{GUEST_ROLE}': ('posts/index.html',),
            f'{url_group}:{GUEST_ROLE}': ('posts/group_list.html',),
            f'{url_profile}:{GUEST_ROLE}': ('posts/profile.html',),
            f'{url_post}:{GUEST_ROLE}': ('posts/post_detail.html', ),
            f'{url_edit}:{GUEST_ROLE}': ('users/login.html',
                                         F'{url_login}?next={url_edit}'),
            f'{url_edit}:{AUTORIZED_ROLE}': ('posts/post_detail.html',
                                             f'{url_post}'),
            f'{url_edit}:{AUTHOR_ROLE}': ('posts/create_post.html', ),
            f'{url_create}:{GUEST_ROLE}': ('users/login.html',
                                           F'{url_login}?next={url_create}'),
            f'{url_create}:{AUTORIZED_ROLE}': ('posts/create_post.html', ),
            f'{url_comment}:{GUEST_ROLE}': ('users/login.html',
                                            F'{url_login}?next={url_comment}'),
            f'{url_comment}:{AUTORIZED_ROLE}': ('posts/post_detail.html',
                                                F'{url_post}'),
            f'{url_follow}:{GUEST_ROLE}': ('users/login.html',
                                           F'{url_login}?next={url_follow}'),
            f'{url_unfollow}:{GUEST_ROLE}': (
                'users/login.html',
                F'{url_login}?next={url_unfollow}'
            ),
            f'{url_follow}:{AUTORIZED_ROLE}': (
                'posts/profile.html',
                url_profile
            ),
            f'{url_unfollow}:{AUTORIZED_ROLE}': (
                'posts/profile.html',
                url_profile
            ),
        }

    def decode_dict_tests(self, case_test: int):
        """функция возвращает список каждый элемент которого:
        list(connection, url, expected)
        на вход принимает код теста:
        0 - тест шаблона и адреса
        1 - тест редиректа адреса"""

        result = list()
        for url_user, data in TaskURLTests.dict_tests.items():
            url, user_name = url_user.split(':')
            client = TaskURLTests.clients[user_name]
            # если выбираем редиректы, то выдаем адреса
            # только те у кого они есть
            if case_test < len(data):
                result.append((client, url, data[case_test]))
        return result

    def test_static(self):
        """Проверяем, что корректно работают статические страницы"""
        static_url_list = (
            ('/', 'posts/index.html'),
            ('/about/author/', 'about/authors.html'),
            ('/about/tech/', 'about/tech.html'),
        )
        # Отправляем запрос через client,
        # по списку статических страниц
        for url, template in static_url_list:
            with self.subTest(url=url):
                response = TaskURLTests.clients[GUEST_ROLE].get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK,
                                 f'Тест статической страницы по адресу: '
                                 f' {url} не пройден!')
                self.assertTemplateUsed(response, template,
                                        f'Ошибка шаблона для страницы {url}'
                                        )

    def test_urls_unexisting(self):
        """Проверяем, url несуществующей страницы"""
        response = TaskURLTests.clients[GUEST_ROLE].get('/unexisting_page/')
        self.assertEqual(response.status_code,
                         HTTPStatus.NOT_FOUND,
                         )

    def urls_and_templates(self):
        """Проверяем, что работают urls для разных ползователей"""
        for test in TaskURLTests.decode_dict_tests(self, 0):
            # test = list(connection, url, expexted)
            client, url, templates = test
            response = client.get(url, follow=True)
            user_name = GUEST_ROLE or response.user.username
            msg = f'{url} не пройден! для клиента {user_name}'
            with self.subTest(url_user_data=(url, user_name, templates)):
                self.assertEqual(response.status_code, HTTPStatus.OK,
                                 'Тест по адресу:' + msg)

                self.assertTemplateUsed(response, templates,
                                        'Тест шаблона по адресу: ' + msg)

    def test_redirect(self):
        """Проверяем, что работают редиректы urls для разных ползователей"""
        for test in TaskURLTests.decode_dict_tests(self, 1):
            # test = list(connection, url, expexted)
            client, url, url_redirect = test
            response = client.get(url, follow=True)
            user_name = GUEST_ROLE or response.user.username
            msg = (f'Тест редиректа по адресу {url} '
                   f'не пройден! для клиента {user_name}')
            with self.subTest(url_user_data=(url, user_name, url_redirect)):
                self.assertRedirects(response,
                                     url_redirect,
                                     msg_prefix=msg
                                     )
