from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PostsConfig(AppConfig):
    name = 'posts'
    verbose_name = _('posts')

    def ready(self):
        import posts.signals
