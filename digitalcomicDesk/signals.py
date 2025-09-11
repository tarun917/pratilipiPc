from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import CommentModel, EpisodeModel


@receiver(post_save, sender=CommentModel)
def incr_episode_comments_count_on_create(sender, instance: CommentModel, created, **kwargs):
    # Only top-level comments affect the denormalized count
    if created and instance.parent is None:
        EpisodeModel.objects.filter(id=instance.episode_id).update(
            comments_count=(instance.episode.comments_count or 0) + 1
        )


@receiver(post_delete, sender=CommentModel)
def decr_episode_comments_count_on_delete(sender, instance: CommentModel, **kwargs):
    if instance.parent is None:
        ep = instance.episode
        new_val = max((ep.comments_count or 0) - 1, 0)
        EpisodeModel.objects.filter(id=ep.id).update(comments_count=new_val)