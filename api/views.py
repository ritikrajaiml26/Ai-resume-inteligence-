from rest_framework import generics, permissions
from resumes.models import Resume, JobDescription, ATSAnalysis
from .serializers import ResumeSerializer, JobDescriptionSerializer, ATSAnalysisSerializer


class ResumeListAPI(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ResumeSerializer

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ResumeDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ResumeSerializer

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)


class JobDescriptionAPI(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JobDescriptionSerializer

    def get_queryset(self):
        return JobDescription.objects.filter(resume__user=self.request.user)


class ATSAnalysisAPI(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ATSAnalysisSerializer
    lookup_field = 'resume_id'

    def get_queryset(self):
        return ATSAnalysis.objects.filter(resume__user=self.request.user)
