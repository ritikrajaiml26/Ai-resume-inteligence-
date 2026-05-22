from resumes.models import Resume


def dashboard_metrics(user):
    resumes = Resume.objects.filter(user=user)
    history = resumes.order_by('-updated_at')[:5]
    return {
        'total_resumes': resumes.count(),
        'recent_history': history,
        'average_score': round(sum([r.ats_analysis.score for r in resumes if hasattr(r, 'ats_analysis')]) / max(1, resumes.count()), 2),
    }
