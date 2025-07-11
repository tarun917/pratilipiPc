from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action

from pratilipiPc import settings
from .models import SubmissionStartSerializer, TermsAndConditions, Submissions, CreatorComics
from .serializers import TermsAndConditionsSerializer, SubmissionSerializer, CreatorComicSerializer
from premiumDesk.models import SubscriptionModel
from notificationDesk.models import NotificationModel
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.authentication import JWTAuthentication
import zipfile
from django.core.files.storage import default_storage
import logging
import os
import boto3
from botocore.exceptions import ClientError
from digitalcomicDesk.models import ComicModel, EpisodeModel
import json

logger = logging.getLogger(__name__)

class CreatorDeskViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=['get'])
    def verify_premium(self, request):
        user = request.user
        is_premium = SubscriptionModel.objects.filter(user=user, end_date__gt=timezone.now()).exists()
        redirect_url = "/api/premium/subscribe/" if not is_premium else None
        return Response({"is_premium": is_premium, "redirect_url": redirect_url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def terms_and_conditions(self, request):
        try:
            terms = TermsAndConditions.objects.latest('created_at')
            serializer = TermsAndConditionsSerializer(terms)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TermsAndConditions.DoesNotExist:
            return Response({"error": "No terms and conditions available"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def accept_terms(self, request):
        user = request.user
        submission = Submissions.objects.create(user=user, t_and_c_accepted=True)
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def start_submission(self, request):
        user = request.user
        data = request.data
        # Check if terms are accepted
        if not user.terms_accepted:  # Assuming CustomUser has terms_accepted field
            return Response({"error": "Terms and Conditions must be accepted before starting a submission. Please visit /accept_terms/."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SubmissionStartSerializer(data=data)
        if serializer.is_valid():
            submission = serializer.save(user=user)
            return Response({"message": "Submission started successfully", "submission_id": str(submission.id)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upload_zip(self, request):
        user = request.user
        submission_id = request.data.get('submission_id')
        submission = get_object_or_404(Submissions, id=submission_id, user=user)

        zip_file = request.FILES.get('zip_file')
        if not zip_file:
            logger.error("No zip file provided for submission %s", submission_id)
            return Response({"error": "No zip file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if zip_file.size > 250 * 1024 * 1024:  # 250 MB in bytes
            logger.error("Zip file exceeds 250MB for submission %s", submission_id)
            return Response({"error": "Zip file size exceeds 250MB"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Store zip file in S3
            zip_path = default_storage.save(f'submissions/{submission_id}.zip', zip_file)
            submission.zip_url = f"{default_storage.url(zip_path)}"

        # Optionally extract cover.png if present
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    if 'cover.png' in [f.filename for f in zip_ref.infolist()]:
                        with zip_ref.open('cover.png') as cover_file:
                            cover_path = default_storage.save(f'submissions/{submission_id}/cover.png', cover_file)
                            submission.cover_url = f"{default_storage.url(cover_path)}"
            except Exception as e:
                logger.warning("No cover.png found or error extracting for submission %s: %s", submission_id, str(e))
                submission.cover_url = None

            submission.save()
            logger.info("Zip file uploaded successfully for submission %s", submission_id)
            serializer = SubmissionSerializer(submission)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Error processing zip file for submission %s: %s", submission_id, str(e))
            return Response({"error": f"Error processing zip file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='submission_status/(?P<submission_id>[0-9A-Fa-f-]+)')
    def submission_status(self, request, submission_id=None):
        submission = get_object_or_404(Submissions, id=submission_id, user=request.user)
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def my_submissions(self, request):
        user = request.user
        submissions = Submissions.objects.filter(user=user).order_by('-submitted_at')
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='admin/submission_zip/(?P<submission_id>[0-9A-Fa-f-]+)', permission_classes=[IsAdminUser])
    def admin_submission_zip(self, request, pk=None, submission_id=None):
        submission = get_object_or_404(Submissions, id=submission_id)
        # Check if S3 is configured
        if all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            s3_client = boto3.client('s3', 
                                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                 region_name=settings.AWS_S3_REGION_NAME)
            try:
                # Extract S3 key from URL (remove domain and bucket prefix)
                zip_key = submission.zip_url.replace(f"http://{settings.AWS_S3_REGION_NAME}.amazonaws.com/{settings.AWS_STORAGE_BUCKET_NAME}/", '').lstrip('/')
                cover_key = submission.cover_url.replace(f"http://{settings.AWS_S3_REGION_NAME}.amazonaws.com/{settings.AWS_STORAGE_BUCKET_NAME}/", '').lstrip('/') if submission.cover_url else None
                zip_url = s3_client.generate_presigned_url('get_object',
                                                       Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                                               'Key': zip_key},
                                                       ExpiresIn=3600)  # 1 hour expiry
                cover_url = s3_client.generate_presigned_url('get_object',
                                                         Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                                                 'Key': cover_key},
                                                         ExpiresIn=3600) if cover_key else None
                return Response({"zip_url": zip_url, "cover_url": cover_url}, status=status.HTTP_200_OK)
            except ClientError as e:
                logger.error("Error generating pre-signed URL for submission %s: %s", submission_id, str(e))
                return Response({"error": "Unable to generate pre-signed URL"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Fallback to local storage paths if S3 is not configured
        return Response({
            "zip_url": submission.zip_url if submission.zip_url else "",
            "cover_url": submission.cover_url if submission.cover_url else ""
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='admin/submission-review', permission_classes=[IsAdminUser])
    def admin_submission_review(self, request):
        submission_id = request.data.get('submission_id')
        new_status = request.data.get('status')
        submission = get_object_or_404(Submissions, id=submission_id)
        # Bypass t_and_c validation for admin review
        if not submission.t_and_c_accepted:
            submission.t_and_c_accepted = True  # Set to True for admin action
        submission.status = new_status
        submission.reviewed_at = timezone.now()
        submission.save()
        NotificationModel.objects.create(
            user=submission.user,
            message=f"Your comic '{submission.title}' is {new_status.lower()}!",
            related_tab='home',
            timestamp=timezone.now()
        )
        logger.info("Notification created for submission %s with status %s", submission_id, new_status)
        return Response({"message": f"Submission {new_status.lower()} and creator notified."}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def home_creators_comics(self, request):
        comics = ComicModel.objects.filter(is_creator_comic=True)
        data = [{"comic_id": c.id, "title": c.title, "cover_url": c.cover_image.url if c.cover_image else None, "stars": float(c.rating), "views": c.view_count} for c in comics]
        # Update HomeTabConfig
        from homeDesk.models import HomeTabConfig
        config, created = HomeTabConfig.objects.get_or_create(key='creators_comics', defaults={'value': '[]'})
        value = json.loads(config.value)
        comic_ids = [c.id for c in comics]
        value.extend([cid for cid in comic_ids if cid not in value])  # Add new comic_ids
        config.value = json.dumps(list(set(value)))  # Avoid duplicates
        config.save()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='admin/manual_upload/(?P<submission_id>\b[0-9A-Fa-f-]+\b)')
    def admin_manual_upload(self, request, submission_id=None):
        submission = get_object_or_404(Submissions, id=submission_id, status='Approved')
        # Create ComicModel
        comic = ComicModel.objects.create(
            title=submission.title,
            genre=submission.genre,
            cover_image=submission.cover_url,  # Assuming cover_url is a valid S3 URL
            description=submission.description,
            is_creator_comic=True
        )
        # Extract and upload PNGs from zip
        s3_client = boto3.client('s3',
                                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                 region_name=settings.AWS_S3_REGION_NAME)
        with default_storage.open(submission.zip_url.replace(f"http://{settings.AWS_S3_REGION_NAME}.amazonaws.com/{settings.AWS_STORAGE_BUCKET_NAME}/", ''), 'rb') as zip_file:
            with zipfile.ZipFile(zip_file) as zip_ref:
                for i in range(1, 11):
                    folder = f"EP{i}"
                    for j in range(1, 6):
                        png_name = f"{folder}/page{j}.png"
                        if png_name in [f.filename for f in zip_ref.infolist()]:
                            with zip_ref.open(png_name) as png_file:
                                s3_key = f'digitalcomics/episodes/{submission_id}/EP{i}/page{j}.png'
                                default_storage.save(s3_key, png_file)
                                EpisodeModel.objects.create(
                                    comic=comic,
                                    episode_number=i,
                                    thumbnail=s3_key if i == 1 else None,  # First episode as thumbnail
                                    content_url=f"{default_storage.url(s3_key)}",
                                    is_free=False,
                                    coin_cost=50,
                                    is_locked=True
                                )
        # Update HomeTabConfig (already handled in home_creators_comics)
        return Response({"message": "Comic and episodes created, HomeTabConfig updated"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def analytics(self, request):
    # Placeholder for analytics logic
        return Response({"message": "Analytics endpoint (future implementation)"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='toggle_draft/(?P<submission_id>[0-9A-Fa-f-]+)')
    def toggle_draft(self, request, submission_id=None):
        return Response({"message": "Draft toggle endpoint (future implementation)"}, status=status.HTTP_200_OK)