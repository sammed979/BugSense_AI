from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def history_page(request):
    """Render history page."""
    return render(request, 'history.html')
