import django_filters
from .models import HistorialMedicoClientas, ContactoDeEmergencia

class filterHistorialMedico(django_filters.FilterSet):
    rut_clienta = django_filters.CharFilter(field_name='id_clienta__rut_clienta', lookup_expr='icontains')

    class Meta:
        model = HistorialMedicoClientas
        fields = ['rut_clienta']

class filterContactoEmergencia(django_filters.FilterSet):
    rut_clienta = django_filters.CharFilter(field_name='id_clienta__rut_clienta', lookup_expr='icontains')

    class Meta:
        model = ContactoDeEmergencia
        fields = ['rut_clienta']