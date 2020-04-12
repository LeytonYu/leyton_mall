from django.urls import path
from .views import name_check, email_check, RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, \
    UserOrderView, AddressView, set_default_addr
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import views as auth_views

app_name = 'user'
urlpatterns = [
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='user/password_reset_form.html',
        email_template_name='user/password_reset_email.html',
        success_url='/user/password-reset-done/'),
         name="password_reset"),
    path('password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='user/password_reset_done.html'),
         name="password_reset_done"),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name="user/password_reset_confirm.html",
                                                     success_url='/user/password-reset-complete/'),
         name="password_reset_confirm"),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='user/password_reset_complete.html'),
         name='password_reset_complete'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name="user/password_change_form.html",
                                                                   success_url="/user/password-change-done/"),
         name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name="user/password_change_done.html"),
         name='password_change_done'),
    path('name_check/', name_check, name='name_check'),
    path('email_check/', email_check, name='email_check'),
    path('register/', RegisterView.as_view(), name='register'),
    path('active/<str:token>', ActiveView.as_view(), name='active'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('order/<int:page>', UserOrderView.as_view(), name='order'),
    path('address/', csrf_exempt(AddressView.as_view()), name='address'),
    path('setdef/', set_default_addr, name='setdef'),
    path('', UserInfoView.as_view(), name='user'),

]
