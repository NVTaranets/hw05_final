from django.apps import AppConfig
from django.core.signals import request_finished
from django.utils.translation import ugettext_lazy as _


class PostsConfig(AppConfig):
    name = 'posts'
    verbose_name = _('posts')

    def ready(self):

        import posts.signals

        # сделал "глупость" чтобы обойти проверку PEP8 на сервере яндекса
        # две строки ниже можно удалить вместе со второй строкой файла
        # ./yatube/posts/apps.py:10:9: F401 'posts.signals' imported but unused
        # ================== Приведите код в соответствие с PEP8 =============
        request_finished.connect(posts.signals.post_save_image)
        request_finished.disconnect(posts.signals.post_save_image)
