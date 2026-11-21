from django.shortcuts import render


def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view — shows a friendly 'Session Expired' page
    instead of Django's default 403 debug screen.
    Auto-redirects to login after 3 seconds (handled in the template).
    """
    return render(request, '403.html', status=403)
