from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def projects_page(request):
    """Render projects page."""
    return render(request, 'projects.html')


@login_required
def project_detail_page(request, pk):
    """Render project detail page."""
    return render(request, 'project_detail.html', {'project_id': pk})
