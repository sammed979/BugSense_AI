from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def workspace_page(request):
    """Render debugging workspace page."""
    return render(request, 'workspace.html')
