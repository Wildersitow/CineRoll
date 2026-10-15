from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
	"""Allow public reads and restrict write requests to staff users."""

	def has_permission(self, request, view):
		return request.method in SAFE_METHODS or bool(
			request.user and request.user.is_staff
		)