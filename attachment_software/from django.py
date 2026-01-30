from django.shortcuts import render

def add_attachee(request):
    return render(request, "accounts/add_attachee.html")