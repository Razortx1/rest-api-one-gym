from django.db.models import Count, Q
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework import filters
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import *
from .serializers import *
import logging
from django.db import connection 
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils.timezone import now
from datetime import datetime,timedelta
from django.utils import timezone
import time

logger = logging.getLogger(__name__)

LAST_UPDATE = timezone.now()

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            logger.warning("Intento de inicio de sesión sin usuario o contraseña.")
            return Response({'error': 'El nombre de usuario y la contraseña son obligatorios.'}, status=400)

        # Autenticación del usuario
        user = authenticate(username=username, password=password)
        if user:
            # Obtén o crea el token
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"Token {'creado' if created else 'recuperado'} para el usuario {user.username}")

            # Intenta obtener el clienta_id y los datos de la clienta
            clienta_id = getattr(user, 'clienta_id', None)
            if clienta_id:
                try:
                    clienta = Clientas.objects.get(id_clienta=clienta_id)
                    clienta_data = ClientasSerializer(clienta).data
                    logger.info(f"Datos de clienta obtenidos para el usuario {user.username}")
                except Clientas.DoesNotExist:
                    logger.error(f"Clienta con id_clienta={clienta_id} no encontrada para el usuario {user.username}")
                    return Response({'error': 'Clienta no encontrada.'}, status=404)
            else:
                logger.warning(f"El usuario {user.username} no tiene clienta_id asociado.")
                clienta_data = None

            # Incluye el token y los datos de la clienta en la respuesta
            return Response({
                'token': token.key,
                'clienta': clienta_data
            }, status=200)
        
        logger.error(f"Credenciales inválidas para el usuario {username}")
        return Response({'error': 'Credenciales inválidas'}, status=401)

def actualizar_fecha_clases():
    """
    Actualiza la fecha de la última modificación de clases.
    """
    global LAST_UPDATE
    LAST_UPDATE = timezone.now()

# --- Función Auxiliar para Obtener Clases Actualizadas ---
def obtener_nuevas_clases():
    """
    Obtiene todas las clases actualizadas de la base de datos.
    """
    clases = HorariosClase.objects.all().values(
        "idhorarios", "clases_id_clase","clases_id_clase__nombre_clase", "fecha_clase", "hora_inicio", "hora_fin", "cupo"
    )
     # Renombrar 'clases_id_clase__nombre_clase' a 'clase_nombre'
    nuevas_clases = []
    for clase in clases:
        clase["clase_nombre"] = clase.pop("clases_id_clase__nombre_clase")
        nuevas_clases.append(clase)
    
    return nuevas_clases

# --- Vista API para Long Polling ---
class LongPollingClasesView(APIView):
    """
    Vista para manejar solicitudes de Long Polling.
    Los clientes envían la última fecha de actualización ('last_update') y
    la vista devuelve los datos si hay cambios en la base de datos.
    """
    def get(self, request):
        # Obtener la fecha de actualización enviada por el cliente
        client_last_update = request.GET.get("last_update")
        start_time = time.time()
        timeout = 30  # Duración máxima de la solicitud en segundos

        try:
            # Convertir la fecha enviada por el cliente a objeto datetime
            if client_last_update:
                client_last_update = timezone.datetime.fromisoformat(client_last_update)
            else:
                client_last_update = None
        except ValueError:
            return Response({"error": "Formato de fecha inválido."}, status=400)

        # Loop para verificar actualizaciones hasta que se alcance el timeout
        while time.time() - start_time < timeout:
            # Comparar la fecha de actualización del servidor con la del cliente
            if not client_last_update or client_last_update < LAST_UPDATE:
                return Response({
                    "actualizado": True,
                    "last_update": LAST_UPDATE.isoformat(),
                    "datos": obtener_nuevas_clases()
                })
            time.sleep(2)  # Espera 2 segundos antes de volver a verificar

        # Si no hay cambios después del timeout, devolvemos actualizado=False
        return Response({"actualizado": False, "last_update": LAST_UPDATE.isoformat()})



class ObtenerClienteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtén el usuario autenticado desde el token
            user = request.user
            clienta_id = self.get_clienta_id(user.id)
            logger.debug(f"Usuario autenticado: {user.username}, clienta_id: {clienta_id}")

            # Verifica si el `clienta_id` es válido
            if clienta_id is None:
                logger.error("clienta_id no encontrado para el usuario.")
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Obtén los datos de la clienta correspondiente
            try:
                clienta = Clientas.objects.get(id_clienta=clienta_id)
                logger.debug(f"Clienta encontrada: {clienta}")
            except Clientas.DoesNotExist:
                logger.error("Clienta no encontrada en la base de datos.")
                return Response({"error": "Clienta no encontrada."}, status=404)

            # Serializa y retorna los datos de la clienta
            serializer = ClientasSerializer(clienta)
            return Response(serializer.data, status=200)

        except Exception as e:
            logger.exception("Error al obtener los datos de la clienta.")
            return Response({"error": f"Error al obtener los datos de la clienta: {str(e)}"}, status=500)
        
class ContactoEmergenciaClientaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        # Consulta directa a la base de datos para obtener el clienta_id del usuario autenticado
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtener el clienta_id del usuario autenticado
            clienta_id = self.get_clienta_id(request.user.id)

            # Verificar si el clienta_id es válido
            if clienta_id is None:
                return Response({"error": "El usuario no tiene un clienta_id asociado."}, status=400)

            # Filtrar los contactos de emergencia de la clienta
            contactos = ContactoDeEmergencia.objects.filter(id_clienta=clienta_id)
            serializer = ContactoDeEmergenciaSerializer(contactos, many=True)
            return Response(serializer.data, status=200)
        
        except Exception as e:
            logger.exception("Error al obtener los datos de contacto de emergencia.")
            return Response({"error": f"Error al obtener los datos de contacto de emergencia: {str(e)}"}, status=500)
        
        
        
class HistorialMedicoClientaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        # Consulta directa a la base de datos para obtener el clienta_id del usuario autenticado
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtener el clienta_id del usuario autenticado
            clienta_id = self.get_clienta_id(request.user.id)

            # Verificar si el clienta_id es válido
            if clienta_id is None:
                return Response({"error": "El usuario no tiene un clienta_id asociado."}, status=400)

            # Filtrar el historial médico de acuerdo al id_clienta
            historial_medico = HistorialMedicoClientas.objects.filter(id_clienta=clienta_id)

            # Verificar si se encontró el historial médico
            if not historial_medico.exists():
                logger.error("Historial médico no encontrado para la clienta.")
                return Response({"error": "Historial médico no encontrado."}, status=404)

            # Serializar y retornar los datos del historial médico
            serializer = HistorialMedicoClientasSerializer(historial_medico, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            # Registro detallado del error para depuración
            logger.exception("Error al obtener los datos del historial médico.")
            return Response({"error": f"Error al obtener los datos del historial médico: {str(e)}"}, status=500)
        
class ClientasHasDisciplinasView(viewsets.ModelViewSet):
    serializer_class = ClientasHasDisciplinasSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Obtén el clienta_id del usuario autenticado
        user = self.request.user
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user.id])
            result = cursor.fetchone()
            clienta_id = result[0] if result else None
        
        # Si no hay clienta_id asociado, devuelve un queryset vacío
        if not clienta_id:
            return ClientasHasDisciplinas.objects.none()

        # Filtra los resultados para incluir solo los registros de esta clienta
        return ClientasHasDisciplinas.objects.filter(clientas_id_clienta=clienta_id)        
    
class ObtenerDisciplinasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtén el usuario autenticado desde el token
            user = request.user
            clienta_id = self.get_clienta_id(user.id)
            logger.debug(f"Usuario autenticado: {user.username}, clienta_id: {clienta_id}")

            # Verifica si el `clienta_id` es válido
            if clienta_id is None:
                logger.error("clienta_id no encontrado para el usuario.")
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Obtén las disciplinas asociadas al cliente
            disciplinas = ClientasHasDisciplinas.objects.filter(clientas_id_clienta=clienta_id)

            if not disciplinas.exists():
                logger.error("No se encontraron disciplinas para la clienta.")
                return Response({"error": "No se encontraron disciplinas para la clienta."}, status=404)

            # Serializa y retorna los datos de las disciplinas
            serializer = ClientasHasDisciplinasSerializer(disciplinas, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            logger.exception("Error al obtener las disciplinas de la clienta.")
            return Response({"error": f"Error al obtener las disciplinas de la clienta: {str(e)}"}, status=500)
        
class ActualizarCupoAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Extraer datos del request
            idhorarios = request.data.get("idhorarios")

            if not idhorarios:
                return Response({"error": "ID del horario es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

            # Bloquear concurrencia y actualizar cupo
            with transaction.atomic():
                try:
                    horario = HorariosClase.objects.select_for_update().get(pk=idhorarios)
                except HorariosClase.DoesNotExist:
                    return Response({"error": "Horario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

                if horario.cupo <= 0:
                    return Response(
                        {"error": "No hay cupos disponibles para esta clase."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Descontar el cupo
                horario.cupo -= 1
                horario.save()

            return Response(
                {
                    "message": "Cupo descontado exitosamente.",
                    "cupo_restante": horario.cupo,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Error al descontar el cupo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RegistrarAsistenciaAPIView(APIView):
   def post(self, request):
        try:
            # Extraer los datos del request
            clientas_id = request.data.get("clientas_id_clienta")
            clases_id = request.data.get("clases_id_clase")
            nombre_clase = request.data.get("nombre_clase")
            fecha_clase = request.data.get("fecha_clase")
            presente = request.data.get("presente", 0)  # Por defecto, 0

            # Validar que todos los campos necesarios están presentes
            if not clientas_id or not clases_id:
                return Response(
                    {"error": "ID de clienta y clase son obligatorios."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Obtener la instancia de la clienta
            try:
                clienta = Clientas.objects.get(pk=clientas_id)
            except Clientas.DoesNotExist:
                return Response({"error": "La clienta no existe."}, status=status.HTTP_404_NOT_FOUND)

            # Obtener la instancia de la clase
            try:
                clase = Clases.objects.get(pk=clases_id)
            except Clases.DoesNotExist:
                return Response({"error": "La clase no existe."}, status=status.HTTP_404_NOT_FOUND)

            # Registrar la asistencia en clientas_has_clases
            ClientasHasClases.objects.create(
                clientas_id_clienta=clienta,  # Usa la instancia de Clientas
                clases_id_clase=clase,        # Usa la instancia de Clases
                nombre_clase=nombre_clase,
                presente=presente,
                fecha_clase=fecha_clase,
            )

            return Response(
                {"message": "Registro en clientas_has_clases completado exitosamente."},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Error al registrar en clientas_has_clases: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
class ObtenerAsistenciasAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            clienta_id = request.user.id  # Asume que el usuario está autenticado
            asistencias = ClientasHasClases.objects.filter(clientas_id_clienta=clienta_id)

            # Obtener horarios relacionados
            data = []
            for asistencia in asistencias:
                # Buscar el horario relacionado con la clase
                horario = HorariosClase.objects.filter(clases_id_clase=asistencia.clases_id_clase).first()
                if horario:
                    data.append({
                        "idhorarios": horario.idhorarios,  # ID del horario
                        "fecha_clase": asistencia.fecha_clase,
                        "nombre_clase": asistencia.nombre_clase,
                        "hora_inicio": horario.hora_inicio,
                        "hora_fin": horario.hora_fin,
                        "cupo": horario.cupo,
                    })
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error al obtener asistencias: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class UpdateClientAPIView(APIView):
    def put(self, request):
        try:
            cliente_data = request.data
            cliente_id = cliente_data.get("id_clienta")
            clienta = Clientas.objects.get(pk=cliente_id)
            serializer = ClientasSerializer(clienta, data=cliente_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Cliente actualizado con éxito"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Clientas.DoesNotExist:
            return Response({"error": "Cliente no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UpdateHistorialAPIView(APIView):
    def put(self, request):
        try:
            data = request.data
            historial_id = data.get("id_historial_medico")
            historial = HistorialMedicoClientas.objects.get(pk=historial_id)
            serializer = HistorialMedicoClientasSerializer(historial, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Historial médico actualizado con éxito"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except HistorialMedicoClientas.DoesNotExist:
            return Response({"error": "Historial médico no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class UpdateContactoAPIView(APIView):
    def put(self, request):
        try:
            data = request.data
            contacto_id = data.get("id_contacto_emergencia")
            contacto = ContactoDeEmergencia.objects.get(pk=contacto_id)
            serializer = ContactoDeEmergenciaSerializer(contacto, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Contacto de emergencia actualizado con éxito"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ContactoDeEmergencia.DoesNotExist:
            return Response({"error": "Contacto de emergencia no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class CantidadClasesActivasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtén el usuario autenticado y su clienta_id
            user = request.user
            clienta_id = self.get_clienta_id(user.id)
            if not clienta_id:
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Consulta la cantidad total de clases activas para la clienta
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(cantidad_clases_disciplina.cantidad_clases) AS total_clases
                    FROM clientas_has_disciplinas
                    JOIN disciplinas ON clientas_has_disciplinas.disciplinas_id_disciplina = disciplinas.id_disciplina
                    JOIN cantidad_clases_disciplina ON disciplinas.id_cantidad_clases_disciplina = cantidad_clases_disciplina.id_cantidad_clases_disciplina
                    WHERE clientas_has_disciplinas.clientas_id_clienta = %s
                    AND clientas_has_disciplinas.estado_membresia = 1
                """, [clienta_id])
                result = cursor.fetchone()
                total_clases = result[0] if result and result[0] else 0

            return Response({"clienta_id": clienta_id, "total_clases": total_clases}, status=200)

        except Exception as e:
            return Response({"error": f"Error al obtener la cantidad de clases: {str(e)}"}, status=500)
        
class ObtenerDisciplinasActivasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtén el usuario autenticado y su clienta_id
            user = request.user
            clienta_id = self.get_clienta_id(user.id)
            if not clienta_id:
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Obtén las disciplinas activas asociadas a la clienta
            disciplinas = ClientasHasDisciplinas.objects.filter(
                clientas_id_clienta=clienta_id, estado_membresia=1
            )

            if not disciplinas.exists():
                return Response({"error": "No se encontraron disciplinas activas para la clienta."}, status=404)

            # Calcular la cantidad total de clases activas
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(cantidad_clases_disciplina.cantidad_clases) AS total_clases
                    FROM clientas_has_disciplinas
                    JOIN disciplinas ON clientas_has_disciplinas.disciplinas_id_disciplina = disciplinas.id_disciplina
                    JOIN cantidad_clases_disciplina ON disciplinas.id_cantidad_clases_disciplina = cantidad_clases_disciplina.id_cantidad_clases_disciplina
                    WHERE clientas_has_disciplinas.clientas_id_clienta = %s
                    AND clientas_has_disciplinas.estado_membresia = 1
                """, [clienta_id])
                result = cursor.fetchone()
                total_clases = result[0] if result and result[0] else 0

            # Serializa las disciplinas activas y añade el total de clases
            serializer = ClientasHasDisciplinasSerializer(disciplinas, many=True)
            response_data = {
                "disciplinas_activas": serializer.data,
                "total_clases_activas": total_clases
            }
            return Response(response_data, status=200)

        except Exception as e:
            return Response({"error": f"Error al obtener las disciplinas activas: {str(e)}"}, status=500)
        
        

class ContarTotalAsistenciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get_clienta_id(self, user_id):
        """
        Obtiene el clienta_id asociado al usuario autenticado.
        """
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Usuario autenticado
            user = request.user
            clienta_id = self.get_clienta_id(user.id)

            if clienta_id is None:
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Obtener todas las clases asociadas a este cliente con filtro 'presente = 1'
            clases = ClientasHasClases.objects.filter(clientas_id_clienta=clienta_id, presente=1)

            # Agrupar las clases por cliente y clase
            clases_list = (
                clases.values('clientas_id_clienta', 'clases_id_clase')
                .annotate(asistencia_count=Count('id_clienta_clase'))
                .order_by('clases_id_clase')  # Ordenar por clase
            )

            # Sumar el total de asistencia_count desde clases_list
            total_asistencias = sum(clase['asistencia_count'] for clase in clases_list)

            # Verificar si hay datos
            if not clases_list:
                return Response({"error": "No se encontraron datos para este cliente."}, status=404)

            # Agregar el total al resultado
            response_data = {
                "clases": list(clases_list),
                "total_asistencia": total_asistencias,  # Total calculado correctamente
            }

            return Response(response_data, status=200)

        except Exception as e:
            return Response(
                {"error": f"Hubo un error al obtener las clases: {str(e)}"},
                status=500,
            )
            
class ClasesFuturasView(APIView):
    permission_classes = [IsAuthenticated]

    def get_clienta_id(self, user_id):
        """
        Obtiene el clienta_id asociado al usuario autenticado.
        """
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtener el clienta_id del usuario autenticado
            user = request.user
            clienta_id = self.get_clienta_id(user.id)

            if clienta_id is None:
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            ahora = timezone.now().date()

            # Filtrar las clases futuras
            clases_futuras = ClientasHasClases.objects.filter(
                clientas_id_clienta=clienta_id,
                fecha_clase__gte=ahora
            ).order_by('fecha_clase')

            # Enriquecer datos con hora_inicio desde HorariosClase
            clases_enriquecidas = []
            for clase in clases_futuras:
                horario = HorariosClase.objects.filter(clases_id_clase=clase.clases_id_clase).first()
                clases_enriquecidas.append({
                    "id_clienta_clase": clase.id_clienta_clase,
                    "clientas_id_clienta": clase.clientas_id_clienta.id_clienta,
                    "clases_id_clase": clase.clases_id_clase.id_clase,
                    "fecha_clase": clase.fecha_clase,
                    "hora_inicio": horario.hora_inicio if horario else "N/A",
                    "nombre_clase": clase.nombre_clase,
                })

            if not clases_enriquecidas:
                return Response({"message": "No se encontraron clases futuras."}, status=404)

            return Response(clases_enriquecidas, status=200)

        except Exception as e:
            logger.exception("Error en ClasesFuturasView")
            return Response(
                {"error": f"Hubo un error al obtener las clases futuras: {str(e)}"},
                status=500,
            )

class BaseCupoAPIView(APIView):
    """
    Clase base para manejo de cupos.
    Permite reutilizar validaciones y lógica de obtención de disciplinas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_disciplina(self, clienta_id, disciplina_id):
        """
        Obtiene la disciplina con bloqueo para actualización.
        """
        if not clienta_id or not disciplina_id:
            raise ValueError("ID de clienta y disciplina son obligatorios.")

        if not isinstance(clienta_id, int) or not isinstance(disciplina_id, int):
            raise TypeError("Los IDs deben ser enteros.")

        # Obtener la disciplina con bloqueo
        try:
            disciplina = ClientasHasDisciplinas.objects.select_for_update().get(
                clientas_id_clienta=clienta_id,
                disciplinas_id_disciplina=disciplina_id
            )
            return disciplina
        except ClientasHasDisciplinas.DoesNotExist:
            raise ClientasHasDisciplinas.DoesNotExist("La disciplina no existe para esta clienta.")

class CancelarAsistenciaAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Extraer datos del request
            clienta_id = request.data.get("clientas_id_clienta")
            clases_id = request.data.get("clases_id_clase")
            id_horario = request.data.get("idhorarios")

            # Validar campos requeridos
            if not clienta_id or not clases_id or not id_horario:
                return Response(
                    {"error": "IDs de clienta, clase y horario son obligatorios."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                # Eliminar el registro de asistencia
                asistencia = ClientasHasClases.objects.filter(
                    clientas_id_clienta=clienta_id,
                    clases_id_clase=clases_id,
                    fecha_clase__gte=now().date()
                )
                if asistencia.exists():
                    asistencia.delete()
                else:
                    return Response(
                        {"error": "No se encontró la asistencia a cancelar."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Actualizar el cupo en HorariosClase
                horario = HorariosClase.objects.select_for_update().get(pk=id_horario)
                horario.cupo += 1
                horario.save()

            return Response(
                {"message": "Asistencia cancelada y cupo sumado exitosamente.", "cupos_restantes": horario.cupo},
                status=status.HTTP_200_OK
            )
        except HorariosClase.DoesNotExist:
            return Response({"error": "Horario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": f"Error al cancelar asistencia: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ObtenerDisciplinasYcuposAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Obtener ID de la clienta autenticada
            clienta_id = request.user.id  # Asegúrate de enlazar el usuario con clienta
            disciplinas = ClientasHasDisciplinas.objects.filter(clientas_id_clienta=clienta_id)

            if not disciplinas.exists():
                return Response({"error": "No se encontraron disciplinas para esta clienta."}, status=status.HTTP_404_NOT_FOUND)

            # Formatear los datos
            disciplinas_data = [
                {
                    "id_disciplina": d.disciplinas_id_disciplina.id_disciplina,
                    "nombre_disciplina": d.nombre_disciplina_contratada,
                    "cupos_disponibles": d.estado_membresia,  # Usa este campo para cupos si es aplicable
                }
                for d in disciplinas
            ]

            return Response({"disciplinas": disciplinas_data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error al obtener disciplinas: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ObtenerDisciplinasYcuposAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Obtener ID de la clienta autenticada
            clienta_id = request.user.id  # Asegúrate de enlazar el usuario con clienta
            disciplinas = ClientasHasDisciplinas.objects.filter(clientas_id_clienta=clienta_id)

            if not disciplinas.exists():
                return Response({"error": "No se encontraron disciplinas para esta clienta."}, status=status.HTTP_404_NOT_FOUND)

            # Formatear los datos
            disciplinas_data = [
                {
                    "id_disciplina": d.disciplinas_id_disciplina.id_disciplina,
                    "nombre_disciplina": d.nombre_disciplina_contratada,
                    "cupos_disponibles": d.estado_membresia,  # Usa este campo para cupos si es aplicable
                }
                for d in disciplinas
            ]

            return Response({"disciplinas": disciplinas_data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error al obtener disciplinas: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FiltrarAsistenciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get_clienta_id(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtener el id_clienta del usuario autenticado
            clienta_id = self.get_clienta_id(request.user.id)
            if not clienta_id:
                return Response({"error": "El usuario no tiene un clienta_id asociado."}, status=400)

            # Obtener el parámetro id_clase desde la URL
            id_clase = request.query_params.get('id_clase')

            # Filtrar las asistencias
            asistencias = ClientasHasClases.objects.filter(
                clientas_id_clienta=clienta_id,
                presente=1
            )

            if id_clase:
                asistencias = asistencias.filter(clases_id_clase=id_clase)

            # Serializar y retornar los datos
            serializer = ClientasHasClasesSerializer(asistencias, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            return Response({"error": f"Error al filtrar asistencias: {str(e)}"}, status=500)
        
class ObtenerDisciplinaActivaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_clienta_id(self, user_id):
        # Obtiene el clienta_id del usuario autenticado
        with connection.cursor() as cursor:
            cursor.execute("SELECT clienta_id FROM auth_user WHERE id = %s", [user_id])
            result = cursor.fetchone()
            return result[0] if result else None

    def get(self, request):
        try:
            # Obtén el clienta_id asociado al usuario autenticado
            user = request.user
            clienta_id = self.get_clienta_id(user.id)

            if not clienta_id:
                return Response({"error": "Este usuario no tiene un clienta_id asociado."}, status=400)

            # Filtra las disciplinas activas (estado_membresia=1) del clienta actual
            disciplinas_activas = ClientasHasDisciplinas.objects.filter(
                clientas_id_clienta=clienta_id, estado_membresia=1
            ).select_related('disciplinas_id_disciplina')

            if not disciplinas_activas.exists():
                return Response({"error": "No se encontraron disciplinas activas para la clienta."}, status=404)

            # Serializa las disciplinas activas
            serializer = ClientasHasDisciplinasSerializer(disciplinas_activas, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            return Response({"error": f"Error al obtener las disciplinas activas: {str(e)}"}, status=500)


# Vistas de modelo con permisos actualizados
class ClientasViewSet(viewsets.ModelViewSet):
    queryset = Clientas.objects.select_related('id_estado_civil')
    serializer_class = ClientasSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^rut_clienta', '^nombres']
    permission_classes = [permissions.AllowAny]

class EstadoCivilViewSet(viewsets.ModelViewSet):
    queryset = EstadoCivil.objects.all()
    serializer_class = EstadoCivilSerializer
    permission_classes = [permissions.AllowAny]

class DisciplinasViewSet(viewsets.ModelViewSet):
    queryset = Disciplinas.objects.select_related('id_instructor').select_related('id_cantidad_clases_disciplina')
    serializer_class = DisciplinasSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^nombre_disciplina']
    permission_classes = [permissions.AllowAny]

class ClasesViewSet(viewsets.ModelViewSet):
    queryset = Clases.objects.select_related('id_disciplina')
    serializer_class = ClasesSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^nombre_clase']
    permission_classes = [permissions.AllowAny]

class CantidadClaseDisciplinaViewSet(viewsets.ModelViewSet):
    queryset = CantidadClasesDisciplina.objects.all()
    serializer_class = CantidadClaseDisciplinaSerializer
    permission_classes = [permissions.AllowAny]

class ClientasHasClasesViewSet(viewsets.ModelViewSet):
    queryset = ClientasHasClases.objects.all()
    serializer_class = ClientasHasClasesSerializer
    permission_classes = [permissions.AllowAny]

class ClientasHasDisciplinasViewSet(viewsets.ModelViewSet):
    queryset = ClientasHasDisciplinas.objects.select_related('clientas_id_clienta').select_related('disciplinas_id_disciplina')
    serializer_class = ClientasHasDisciplinasSerializerSecond
    permission_classes = [permissions.AllowAny]

class ContactoDeEmergenciaViewSet(viewsets.ModelViewSet):
    queryset = ContactoDeEmergencia.objects.all()
    serializer_class = ContactoDeEmergenciaSerializer
    permission_classes = [permissions.AllowAny]

class HistorialMedicoClientasViewSet(viewsets.ModelViewSet):
    queryset = HistorialMedicoClientas.objects.select_related('id_clienta')
    serializer_class = HistorialMedicoClientasSerializer
    filter_backends = [filters.SearchFilter]
    permission_classes = [permissions.AllowAny]

class HorariosClaseViewSet(viewsets.ModelViewSet):
    queryset = HorariosClase.objects.select_related('clases_id_clase')
    serializer_class = HorariosClaseSerializerSecond
    permission_classes = [permissions.AllowAny]

class InstructoresViewSet(viewsets.ModelViewSet):
    queryset = Instructores.objects.all()
    serializer_class = InstructoresSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^rut_instructor', '^nombres']
    permission_classes = [permissions.AllowAny]


# Vista personalizada para contar clases asistidas
class ContadorClientaClasesViewSet(viewsets.ModelViewSet):
    queryset = ClientasHasClases.objects.all()
    serializer_class = ContadorClientaClaseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Contar solo donde 'presente' es 1
        return super().get_queryset().values('clientas_id_clienta', 'clases_id_clase').annotate(
            asistencia_count=Count('id_clienta_clase', filter=Q(presente=1))
        )

class ContadorClientaApiView(APIView):
    serializer_class = ContarClientasSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        contador_clienta = Clientas.objects.count()

        return Response({'contador_clientas': contador_clienta}, status=status.HTTP_200_OK)
        