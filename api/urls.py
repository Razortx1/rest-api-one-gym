from django.urls import path, include, re_path
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()

# Registro de vistas
router.register(r'clientas', ClientasViewSet, basename='clientas')
router.register(r'estado-civil', EstadoCivilViewSet, basename='estado_civil')
router.register(r'disciplinas', DisciplinasViewSet, basename='disciplinas')
router.register(r'clases', ClasesViewSet, basename='clases')
router.register(r'cantidad-clase-disciplina', CantidadClaseDisciplinaViewSet, basename='cantidad_clase_disciplina')
router.register(r'clientas-clases', ClientasHasClasesViewSet, basename='clientas_clases')
router.register(r'clientas-disciplina', ClientasHasDisciplinasViewSet, basename='clientas_disciplina')
router.register(r'contacto-emergencia', ContactoDeEmergenciaViewSet, basename='contacto_emergencia')
router.register(r'historial-medico', HistorialMedicoClientasViewSet, basename='historial_medico')
router.register(r'horario-clase', HorariosClaseViewSet, basename='horario_clase')
router.register(r'instructores', InstructoresViewSet, basename='instructores')
router.register(r'contar-clienta-clase', ContadorClientaClasesViewSet, basename='contar_clienta_clase')

# Agregar la URL de inicio de sesión
urlpatterns = [
path('login/', LoginView.as_view(), name='login'),
    path('obtener_cliente/', ObtenerClienteView.as_view(), name='obtener_cliente'),
    path('api/', include(router.urls)),  # Para tener un prefijo común 'api/'
    path('api/contacto-emergencia-clienta/', ContactoEmergenciaClientaView.as_view(), name='contacto_emergencia_clienta'),
    path('api/historial-medico-clienta/', HistorialMedicoClientaView.as_view(), name='historial_medico_clienta'),
    path('api/disciplinas-clienta/', ObtenerDisciplinasView.as_view(),name ='disciplinas_clienta'),
    path('api/actualizar-cupo/', ActualizarCupoAPIView.as_view(), name='actualizar_cupo'),
    path("api/registrar-asistencia/", RegistrarAsistenciaAPIView.as_view(), name="registrar_asistencia"),
    path("api/obtener-asistencias/", ObtenerAsistenciasAPIView.as_view(), name="obtener_asistencias"),
    path("api/update-client/", UpdateClientAPIView.as_view(), name="update-client"),
    path("api/update-historial/", UpdateHistorialAPIView.as_view(), name="update-historial"),
    path("api/update-contacto/", UpdateContactoAPIView.as_view(), name="update-contacto"), 
    path('api/cantidad-clases-activas/', CantidadClasesActivasView.as_view(), name='cantidad_clases_activas'),
    path('api/disciplinas-activas/', ObtenerDisciplinasActivasView.as_view(), name='disciplinas_activas'),
    path('api/contar-total-asistencia/', ContarTotalAsistenciaView.as_view(), name='contar-total-asistencia'),
    path('api/clases-futuras/', ClasesFuturasView.as_view(),name='clases-futuras'),
    path('api/disciplinas-y-cupos/', ObtenerDisciplinasYcuposAPIView.as_view(), name='disciplinas_y_cupos'),
    path('api/cancelar-asistencia/', CancelarAsistenciaAPIView.as_view(), name="cancelar_asistencia"),  # Descontar cupo de una disciplina cuando se registra una asistencia.  # Para tener un prefijo común 'api/'  # Para tener un prefijo común 'api/'  # Para tener un prefijo com
    path('api/contar-clientas', ContadorClientaApiView.as_view(), name='contar-clientas')
]


# Agregar las URLs del enrutador
urlpatterns += router.urls
