from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def learning_page(request):
    """Render learning centre page."""
    return render(request, 'learning.html')
