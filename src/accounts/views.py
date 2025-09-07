from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.models import User


class SignUpView(CreateView):
    """회원가입 뷰"""
    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '회원가입이 완료되었습니다. 로그인해주세요.')
        return response


def login_view(request):
    """로그인 뷰"""
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'{username}님, 환영합니다!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
        else:
            messages.error(request, '사용자명 또는 비밀번호가 올바르지 않습니다.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """로그아웃 뷰"""
    user_name = request.user.username
    logout(request)
    messages.success(request, f'{user_name}님, 안전하게 로그아웃되었습니다.')
    return redirect('accounts:login')


def profile_view(request):
    """프로필 뷰"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    context = {
        'user': request.user,
        'user_stats': {
            'date_joined': request.user.date_joined,
            'last_login': request.user.last_login,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
        }
    }
    return render(request, 'accounts/profile.html', context)
