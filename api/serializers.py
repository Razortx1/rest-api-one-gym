from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
        
class EstadoCivilSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCivil
        fields = ['id_estado_civil' ,'tipo_estado_civil']

class ClientasSerializer(serializers.ModelSerializer):
    tipo_estado_civil = serializers.CharField(source='id_estado_civil.tipo_estado_civil', read_only=True)
    class Meta:
        model = Clientas
        fields = '__all__'

class CantidadClaseDisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CantidadClasesDisciplina
        fields = '__all__'

class ClientasHasClasesSerializer(serializers.ModelSerializer):
    clientas_id_clienta = serializers.PrimaryKeyRelatedField(queryset=Clientas.objects.all())
    clases_id_clase = serializers.PrimaryKeyRelatedField(queryset=Clases.objects.all())

    class Meta:
        model = ClientasHasClases
        fields = '__all__'
        
class ClientasHasDisciplinasSerializer(serializers.ModelSerializer):
    nombre_disciplina = serializers.CharField(source='disciplinas_id_disciplina.nombre_disciplina', read_only=True)
    class Meta:
        model = ClientasHasDisciplinas
        fields = [
            'id_clienta_disciplina',
            'clientas_id_clienta',
            'disciplinas_id_disciplina',
            'nombre_disciplina',
            'nombre_disciplina_contratada',
            'duracion_disciplina',
            'fecha_inscripcion',
            'fecha_termino',
            'estado_membresia',
        ]

class ContactoDeEmergenciaSerializer(serializers.ModelSerializer):
    nombre_clienta = serializers.CharField(source= 'id_clienta.nombres', read_only=True)
    rut_clienta = serializers.CharField(source= 'id_clienta.rut_clienta', read_only=True)
    class Meta:
        model = ContactoDeEmergencia
        fields = '__all__'

class HistorialMedicoClientasSerializer(serializers.ModelSerializer):
    nombre_clienta = serializers.CharField(source= 'id_clienta.nombres', read_only=True)
    rut_clienta = serializers.CharField(source= 'id_clienta.rut_clienta', read_only=True)
    class Meta:
        model = HistorialMedicoClientas
        fields = ['id_historial_medico','id_clienta', 'tiene_alergias', 'detalle_alergia', 'tiene_cirugias', 'detalle_cirugia',
                  'tiene_enfermedades', 'detalle_enfermedad', 'nombre_clienta', 'rut_clienta']

class HorariosClaseSerializer(serializers.ModelSerializer):
    clase_nombre = serializers.CharField(source='clases_id_clase.nombre_clase', read_only=True)

    class Meta:
        model = HorariosClase
        fields = '__all__'

class InstructoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructores
        fields = '__all__'

class DisciplinasSerializer(serializers.ModelSerializer):
    nombres_instructor = serializers.CharField(source='id_instructor.nombres', read_only=True)
    rut_instructor = serializers.CharField(source='id_instructor.rut_instructor', read_only=True)
    cantidad_clases = serializers.CharField(source='id_cantidad_clases_disciplina.cantidad_clases', read_only=True)
    class Meta:
        model = Disciplinas
        fields = ['id_disciplina', 'nombre_disciplina', 'descripcion_disciplina', 'rango_horarios', 'nombres_instructor', 
                  'rut_instructor', 'cantidad_clases', 'id_instructor', 'id_cantidad_clases_disciplina']
        read_only = 'id_disciplina'

class ClasesSerializer(serializers.ModelSerializer):
    nombre_disciplina = serializers.CharField(source='id_disciplina.nombre_disciplina', read_only=True)
    class Meta:
        model = Clases
        fields = '__all__'

class ClientasHasDisciplinasSerializerSecond(serializers.ModelSerializer):
    nombre_disciplina = serializers.CharField(source='disciplinas_id_disciplina.nombre_disciplina', read_only=True)
    nombre_clienta = serializers.CharField(source= 'clientas_id_clienta.nombres', read_only=True)
    rut_clienta = serializers.CharField(source='clientas_id_clienta.rut_clienta', read_only=True)
    class Meta:
        model = ClientasHasDisciplinas
        fields = [
            'id_clienta_disciplina',
            'clientas_id_clienta',
            'nombre_clienta',
            'rut_clienta',
            'disciplinas_id_disciplina',
            'nombre_disciplina',
            'nombre_disciplina_contratada',
            'duracion_disciplina',
            'fecha_inscripcion',
            'fecha_termino',
            'estado_membresia',
        ]

class ClientasHasClasesSerializer(serializers.ModelSerializer):
    nombre_clienta = serializers.CharField(source = 'clientas_id_clienta.nombres', read_only=True)
    rut_clienta = serializers.CharField(source = 'clientas_id_clienta.rut_clienta', read_only=True)
    nombre_clase = serializers.CharField(source = 'clases_id_clase.nombre_clase', read_only = True)
    class Meta:
        model = ClientasHasClases
        fields = '__all__'
        
class HorariosClaseSerializerSecond(serializers.ModelSerializer):
    nombre_clase = serializers.CharField(source = 'clases_id_clase.nombre_clase', read_only = True)
    class Meta:
        model = HorariosClase
        fields = '__all__'

class ContadorClientaClaseSerializer(serializers.ModelSerializer):
    clientas_id_clienta = serializers.IntegerField()
    clases_id_clase = serializers.IntegerField()
    asistencia_count = serializers.IntegerField()
    asistencia_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = ClientasHasClases
        fields = ['clientas_id_clienta', 'clases_id_clase','asistencia_count']


class ContarClientasSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Clientas
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    clienta = serializers.PrimaryKeyRelatedField(queryset=Clientas.objects.all(), source='userprofile.clienta')

    class Meta:
        model = User
        fields = ['id','username', 'email', 'password', 'clienta']

    def create(self, validated_data):
        # Extraemos la clienta de los datos validados
        clienta = validated_data.pop('userprofile', None)  # Asegúrate de que 'userprofile' esté bien configurado
        password = validated_data.pop('password')
        
        # Crear el usuario (sin la relación con Clienta todavía)
        user = User.objects.create(**validated_data)

        # Cifrar la contraseña antes de guardarla
        user.set_password(password)
        user.save()

        # Crear el UserProfile asociado con la Clienta
        if clienta:
            UserProfile.objects.create(user=user, clienta=clienta['clienta'])
        return user

    def update(self, instance, validated_data):
        # Primero extraemos el campo 'clienta' del validated_data
        clienta_data = validated_data.pop('userprofile', None)
        
        # Si se ha proporcionado una nueva contraseña, la extraemos y la ciframos
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # Actualizamos los demás campos del usuario
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()  # Guardamos el usuario actualizado

        # Ahora actualizamos la relación con UserProfile
        if clienta_data:
            # Si ya existe un UserProfile para este usuario, lo actualizamos
            user_profile = instance.userprofile  # La relación con UserProfile ya existe
            user_profile.clienta = clienta_data['clienta']
            user_profile.save()  # Guardamos el UserProfile actualizado

        return instance