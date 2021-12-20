from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from posts.models import Post
from sorl.thumbnail import delete


@receiver(post_delete, sender=Post)
def post_save_image(sender, instance, *args, **kwargs):
    """ Clean Old Image file """
    try:
        old_img = instance.__class__.objects.get(id=instance.id).image.name
        # instance.image.delete(save=False)
        delete(old_img)
    except Exception:
        pass


@receiver(pre_save, sender=Post)
def pre_save_image(sender, instance, *args, **kwargs):
    """ instance old image file will delete from os """

    try:
        old_img = instance.__class__.objects.get(id=instance.id).image.name
        try:
            new_img = instance.image.name
        except Exception:
            new_img = None
        if new_img != old_img:
            delete(old_img)
    except Exception:
        pass
