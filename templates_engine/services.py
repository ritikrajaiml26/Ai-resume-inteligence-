from django.template.loader import render_to_string
from resumes.models import Resume


def build_template_html(resume: Resume, style='corporate'):
    context = {'resume': resume}
    if style == 'modern':
        template_name = 'templates_engine/modern.html'
    elif style == 'minimal':
        template_name = 'templates_engine/minimal.html'
    else:
        template_name = 'templates_engine/corporate.html'
    return render_to_string(template_name, context)
