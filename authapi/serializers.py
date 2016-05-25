from django.contrib.auth.models import User
from rest_framework import serializers

from authapi.models import SeedOrganization, SeedTeam, SeedPermission


class SerializerPkField(serializers.PrimaryKeyRelatedField):
    '''Field that uses a serializer representation when reading the field, but
    a primary key value when writing to the field.'''
    def __init__(self, **kwargs):
        self.serializer = kwargs.pop('serializer')
        return super(SerializerPkField, self).__init__(**kwargs)

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return self.serializer(instance=value, context=self.context).data


class OrganizationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedOrganization
        fields = ('id', 'url')


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url')


class TeamSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedTeam
        fields = ('id', 'url')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedPermission
        fields = ('id', 'type', 'object_id', 'namespace')


class ExistingUserSerializer(serializers.Serializer):
    '''Serializer for adding/removing an existing user.'''
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all())


class OrganizationSerializer(serializers.ModelSerializer):
    teams = TeamSummarySerializer(
        many=True, source='get_active_teams', read_only=True)
    users = UserSummarySerializer(
        many=True, source='get_active_users', read_only=True)

    class Meta:
        model = SeedOrganization
        fields = ('title', 'id', 'url', 'teams', 'users', 'archived')


class TeamSerializer(serializers.ModelSerializer):
    users = UserSummarySerializer(
        many=True, read_only=True, source='get_active_users')
    permissions = PermissionSerializer(many=True, read_only=True)
    organization = SerializerPkField(
        serializer=OrganizationSummarySerializer,
        queryset=SeedOrganization.objects.all())

    class Meta:
        model = SeedTeam
        fields = (
            'id', 'title', 'permissions', 'users', 'url', 'organization',
            'archived')


class UserSerializer(serializers.ModelSerializer):
    teams = TeamSummarySerializer(
        many=True, source='seedteam_set', read_only=True)
    organizations = OrganizationSummarySerializer(
        many=True, source='seedorganization_set', read_only=True)
    email = serializers.EmailField()
    admin = serializers.BooleanField(source='is_superuser', required=False)
    password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)
    active = serializers.BooleanField(default=True, source='is_active')

    class Meta:
        model = User
        fields = (
            'id', 'url', 'first_name', 'last_name', 'email', 'admin', 'teams',
            'organizations', 'password', 'active')

    def create(self, validated_data):
        '''We want to set the username to be the same as the email, and use the
        correct create function to make use of password hashing.'''
        validated_data['username'] = validated_data['email']
        admin = validated_data.pop('is_superuser', None)

        if admin is True:
            user = User.objects.create_superuser(**validated_data)
        else:
            user = User.objects.create_user(**validated_data)

        return user

    def update(self, instance, validated_data):
        '''We want to set all the required fields if admin is set, and we want
        to use the password hashing method if password is set.'''
        admin = validated_data.pop('is_superuser', None)
        password = validated_data.pop('password', None)
        if validated_data.get('email') is not None:
            validated_data['username'] = validated_data['email']

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if admin is not None:
            instance.is_staff = admin
            instance.is_superuser = admin
        if password is not None:
            instance.set_password(password)

        instance.save()
        return instance
