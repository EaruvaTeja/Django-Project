"""
Users App — Address API URLs

Included under /api/addresses/ in the main project URLs.

Routes:
    GET    /api/addresses/                    -> list user's addresses
    POST   /api/addresses/                    -> create a new address
    GET    /api/addresses/<pk>/               -> single address
    PATCH  /api/addresses/<pk>/               -> update address
    DELETE /api/addresses/<pk>/               -> remove address
    POST   /api/addresses/<pk>/set-default/   -> mark as default
"""

from django.urls import path

from . import api_views


app_name = 'address_api'


urlpatterns = [
    path(
        '',
        api_views.AddressListCreateAPIView.as_view(),
        name='address-list-create',
    ),
    path(
        '<int:pk>/',
        api_views.AddressDetailAPIView.as_view(),
        name='address-detail',
    ),
    path(
        '<int:pk>/set-default/',
        api_views.AddressSetDefaultAPIView.as_view(),
        name='address-set-default',
    ),
]