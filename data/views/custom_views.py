import json

from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from users.models import Account
from data.api import validate_request
from data.custom_models import CustomTable, CustomField, CustomRecord, CustomData
from shared.auth import check_authentication


class CustomTableView(APIView):

    authentication_classes = (TokenAuthentication,)

    # GET /tables
    def __get_list(self, request, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_tables = CustomTable.objects.filter(account=account)
            return Response([
                custom_table.get_api_format()
                for custom_table in custom_tables
            ], status=status.HTTP_200_OK)

        except Account.DoesNotExist as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # GET /tables/:id
    def __get_one(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            return Response(custom_table.get_api_format(),
                            status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None, format=None):
        if id:
            return self.__get_one(request, id, format=format)
        else:
            return self.__get_list(request, format=format)

    # POST /tables
    def __post_create(self, request, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = validate_request(json.loads(request.body),
                                            CustomTable.REQUIRED_FIELDS)

            custom_table = CustomTable.create_from_api(user, request_json)

            return Response(custom_table.get_api_format(),
                            status=status.HTTP_201_CREATED)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except Account.DoesNotExist as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # POST /tables/:id
    def __post_update(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = json.loads(request.body)
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_table = custom_table.update_from_api(user, request_json)

            return Response(custom_table.get_api_format(),
                            status=status.HTTP_200_OK)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, id=None, format=None):
        if id:
            return self.__post_update(request, id, format=format)
        else:
            return self.__post_create(request, format=format)

    # DELETE /tables/:id
    def delete(self, request, id=None, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            table_id = int(id)

            CustomTable.objects.get(account=account, id=table_id,
                                    owner=user).delete()
            return Response({ 'id': table_id }, status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

class CustomFieldView(APIView):

    authentication_classes = (TokenAuthentication,)

    # GET /tables/:table_id/fields
    def __get_list(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_fields = CustomField.objects.filter(account=account,
                                                       table=custom_table)
            return Response([
                custom_field.get_api_format()
                for custom_field in custom_fields
            ], status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # GET /tables/:table_id/fields/:field_id
    def __get_one(self, request, table_id, field_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_field = CustomField.objects.get(account=account, id=field_id,
                                                   table=custom_table)
            return Response(custom_field.get_api_format(),
                            status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomField.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, table_id, field_id=None, format=None):
        if field_id:
            return self.__get_one(request, table_id, field_id, format=format)
        else:
            return self.__get_list(request, table_id, format=format)

    # POST /tables/:table_id/fields
    def __post_create(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = validate_request(json.loads(request.body),
                                            CustomField.REQUIRED_FIELDS)
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_field = CustomField.create_from_api(user, custom_table,
                                                       request_json)
            return Response(custom_field.get_api_format(),
                            status=status.HTTP_201_CREATED)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # POST /tables/:table_id/fields/:field_id
    def __post_update(self, request, table_id, field_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = json.loads(request.body)
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_field = CustomField.objects.get(account=account, id=field_id,
                                                   table=custom_table)
            custom_field = custom_field.update_from_api(user, custom_table,
                                                        request_json)
            return Response(custom_field.get_api_format(),
                            status=status.HTTP_200_OK)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomField.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, table_id, field_id=None, format=None):
        if field_id:
            return self.__post_update(request, table_id, field_id,
                                      format=format)
        else:
            return self.__post_create(request, table_id, format=format)

    # DELETE /tables/:table_id/fields/:field_id
    def delete(self, request, table_id, field_id=None, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            table_id = int(table_id)
            field_id = int(field_id)

            custom_table = CustomTable.objects.get(account=account, id=table_id,
                                                   owner=user)
            CustomField.objects.get(account=account, id=field_id, owner=user,
                                    table=custom_table).delete()
            return Response({ 'id': field_id }, status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomField.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

class CustomRecordView(APIView):

    authentication_classes = (TokenAuthentication,)

    # GET /tables/:table_id/records
    def __get_list(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_records = CustomRecord.objects.filter(account=account,
                                                         table=custom_table)
            return Response([
                custom_record.get_api_format()
                for custom_record in custom_records
            ], status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # GET /tables/:table_id/records/:record_id
    def __get_one(self, request, table_id, record_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_record = CustomRecord.objects.get(account=account,
                                                     id=record_id,
                                                     table=custom_table)
            return Response(custom_record.get_api_format(),
                            status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomRecord.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, table_id, record_id=None, format=None):
        if record_id:
            return self.__get_one(request, table_id, record_id, format=format)
        else:
            return self.__get_list(request, table_id, format=format)

    # POST /tables/:table_id/records
    def __post_create(self, request, table_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = validate_request(json.loads(request.body),
                                            CustomRecord.REQUIRED_FIELDS)
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_record = CustomRecord.create_from_api(user, custom_table,
                                                         request_json)
            return Response(custom_record.get_api_format(),
                            status=status.HTTP_201_CREATED)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except (Account.DoesNotExist, CustomTable.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    # POST /tables/:table_id/records/:record_id
    def __post_update(self, request, table_id, record_id, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            request_json = json.loads(request.body)
            custom_table = CustomTable.objects.get(account=account, id=table_id)
            custom_record = CustomRecord.objects.get(account=account,
                                                     id=record_id,
                                                     table=custom_table)
            custom_record = custom_record.update_from_api(user, custom_table,
                                                          request_json)
            return Response(custom_record.get_api_format(),
                            status=status.HTTP_200_OK)

        except (TypeError, ValueError) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)
        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomRecord.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, table_id, record_id=None, format=None):
        if record_id:
            return self.__post_update(request, table_id, record_id,
                                      format=format)
        else:
            return self.__post_create(request, table_id, format=format)

    # DELETE /tables/:table_id/records/:record_id
    def delete(self, request, table_id, record_id=None, format=None):
        try:
            user = check_authentication(request)
            account = user.account
            table_id = int(table_id)
            record_id = int(record_id)

            custom_table = CustomTable.objects.get(account=account, id=table_id,
                                                   owner=user)
            CustomRecord.objects.get(account=account, id=record_id, owner=user,
                                    table=custom_table).delete()
            return Response({ 'id': record_id }, status=status.HTTP_200_OK)

        except (Account.DoesNotExist, CustomTable.DoesNotExist,
                CustomRecord.DoesNotExist) as e:
            return Response({ 'error': str(e) },
                            status=status.HTTP_400_BAD_REQUEST)