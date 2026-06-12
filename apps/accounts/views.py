from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:painel")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(request.GET.get("next", "dashboard:painel"))
        else:
            messages.error(request, "Usuário ou senha incorretos.")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")
