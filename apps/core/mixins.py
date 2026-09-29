from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class RegularUserRequiredMixin(UserPassesTestMixin):
    """Mixin untuk memastikan hanya user biasa (bukan staff/admin) yang bisa mengakses halaman."""
    def test_func(self):
        return self.request.user.is_authenticated and not self.request.user.is_staff