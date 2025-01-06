from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token as DefaultToken

class CustomToken(models.Model):
    user = models.OneToOneField(User, related_name='custom_token', on_delete=models.CASCADE)
    key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = DefaultToken.objects.create(user=self.user).key
        super().save(*args, **kwargs)
class Auth(models.Model):
    idauth = models.AutoField(db_column='idAuth', primary_key=True)  # Field name made lowercase.

    class Meta:
        db_table = 'auth'


class CantidadClasesDisciplina(models.Model):
    id_cantidad_clases_disciplina = models.AutoField(primary_key=True)
    cantidad_clases = models.IntegerField()

    class Meta:
        db_table = 'cantidad_clases_disciplina'


class Clases(models.Model):
    id_clase = models.AutoField(primary_key=True)
    id_disciplina = models.ForeignKey('Disciplinas', models.CASCADE, db_column='id_disciplina')
    nombre_clase = models.CharField(max_length=45, blank=True, null=True)

    def __str__(self):
        return self.nombre_clase

    class Meta:
        db_table = 'clases'


class Clientas(models.Model):
    id_clienta = models.AutoField(primary_key=True)
    rut_clienta = models.CharField(max_length=45, unique=True, null=False)
    nombres = models.CharField(max_length=80)
    apellido_paterno = models.CharField(max_length=45)
    apellido_materno = models.CharField(max_length=45)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=45)
    id_estado_civil = models.ForeignKey('EstadoCivil', models.CASCADE, db_column='id_estado_civil')
    ocupacion = models.CharField(max_length=45)
    fecha_de_nacimiento = models.DateField()
    biometria_facial = models.TextField(blank=True, null=True)

    
    def __str__(self):
        return self.nombres

    class Meta:
        db_table = 'clientas'


class ClientasHasClases(models.Model):
    id_clienta_clase = models.AutoField(primary_key=True)
    clientas_id_clienta = models.ForeignKey(Clientas, models.CASCADE, db_column='Clientas_id_clienta')
    clases_id_clase = models.ForeignKey(Clases, models.CASCADE, db_column='Clases_id_clase')
    nombre_clase = models.CharField(max_length=45, blank=True, null=True)
    presente = models.IntegerField(blank=True, null=True)
    hora_llegada = models.TimeField(blank=True, null=True)
    fecha_clase = models.DateField(blank=True, null=True)  # Nuevo campo

    class Meta:
        db_table = 'clientas_has_clases'


class ClientasHasDisciplinas(models.Model):
    id_clienta_disciplina = models.AutoField(primary_key=True)
    clientas_id_clienta = models.ForeignKey(Clientas, models.CASCADE, db_column='Clientas_id_clienta')  # Field name made lowercase. The composite primary key (Clientas_id_clienta, Disciplinas_id_disciplina) found, that is not supported. The first column is selected.
    disciplinas_id_disciplina = models.ForeignKey('Disciplinas', models.CASCADE, db_column='Disciplinas_id_disciplina')  # Field name made lowercase.
    nombre_disciplina_contratada = models.CharField(max_length=120, blank=True, null=True)
    duracion_disciplina = models.CharField(max_length=50, blank=True, null=True)
    fecha_inscripcion = models.DateField(blank=True, null=True)
    fecha_termino = models.DateField(max_length=45, blank=True, null=True)
    estado_membresia = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'clientas_has_disciplinas'


class ContactoDeEmergencia(models.Model):
    id_contacto_emergencia = models.AutoField(primary_key=True)
    id_clienta = models.ForeignKey(Clientas, models.CASCADE, db_column='id_clienta')
    nombre_contacto_emergencia = models.CharField(max_length=80)
    numero_contacto_emergencia = models.CharField(max_length=25)
    correo_contacto_emergencia = models.CharField(max_length=120)
    tipo_contacto_emergencia = models.CharField(max_length=35)

    class Meta:
        db_table = 'contacto_de_emergencia'


class Disciplinas(models.Model):
    id_disciplina = models.AutoField(primary_key=True)
    id_instructor = models.ForeignKey('Instructores', models.CASCADE, db_column='id_instructor')
    id_cantidad_clases_disciplina = models.ForeignKey(CantidadClasesDisciplina, models.CASCADE, db_column='id_cantidad_clases_disciplina')
    nombre_disciplina = models.CharField(max_length=120, blank=True, null=True)
    descripcion_disciplina = models.TextField(blank=True, null=True)
    rango_horarios = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        db_table = 'disciplinas'
    def __str__(self):
        return self.nombre_disciplina


class EstadoCivil(models.Model):
    id_estado_civil = models.AutoField(primary_key=True)
    tipo_estado_civil = models.CharField(max_length=45)

    class Meta:
        db_table = 'estado_civil'
    def __str__(self):
        return self.tipo_estado_civil


class HistorialMedicoClientas(models.Model):
    id_historial_medico = models.AutoField(primary_key=True)
    id_clienta = models.ForeignKey(Clientas, models.CASCADE, db_column='id_clienta')
    tiene_alergias = models.IntegerField()
    detalle_alergia = models.TextField(blank=True, null=True)
    tiene_cirugias = models.IntegerField()
    detalle_cirugia = models.TextField(blank=True, null=True)
    tiene_enfermedades = models.IntegerField()
    detalle_enfermedad = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'historial_medico_clientas'


class HorariosClase(models.Model):
      idhorarios = models.AutoField(primary_key=True)
      clases_id_clase = models.ForeignKey('Clases', on_delete=models.CASCADE, db_column='Clases_id_clase')
      fecha_clase = models.DateField()
      hora_inicio = models.TimeField()
      hora_fin = models.TimeField()
      cupo = models.PositiveIntegerField(default=20)  # Valor predeterminado
      
      class Meta:
          db_table = 'horarios_clase'
  

class Instructores(models.Model):
    id_instructor = models.AutoField(primary_key=True)
    rut_instructor = models.CharField(max_length=45, unique=True, null=False)
    nombres = models.CharField(max_length=80)
    apellido_paterno = models.CharField(max_length=80)
    apellido_materno = models.CharField(max_length=80)
    esta_activo = models.IntegerField()

    class Meta:
        db_table = 'instructores'

    def __str__(self) -> str:
        return self.nombres
        
