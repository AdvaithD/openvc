import json
from django.db import models
from shared.utils import parse_date

class Investor(models.Model):
    name       = models.TextField()
    type       = models.TextField()

class Person(models.Model):

    def _get_full_name(self):
        names = [n for n in [self.first_name, self.last_name] if n]
        return ' '.join(names)

    first_name = models.TextField()
    last_name  = models.TextField()
    email      = models.EmailField(null=True, blank=True, unique=True)
    location   = models.TextField(null=True, blank=True)
    gender     = models.TextField(null=True, blank=True)
    race       = models.TextField(null=True, blank=True)
    website    = models.TextField(null=True, blank=True)
    photo_url  = models.TextField(null=True, blank=True)
    # Should be unique, but don't add a constraint for more flexibility around
    # user input.
    linkedin_url = models.TextField(null=True, blank=True)
    investor   = models.OneToOneField(Investor, unique=True, null=True,
                                      blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_name = property(_get_full_name)

    def __unicode__(self):
        return self.full_name

    def __get_current_employment(self):
        return (self.employment.filter(current=True)
                               .order_by('end_date', 'start_date',
                                         'company__name', 'title'))
    def __get_null_employment(self):
        """Assume None in end_date implies present"""
        return (self.employment.filter(end_date__isnull=True)
                               .exclude(current=True)
                               .order_by('end_date', 'start_date',
                                         'company__name', 'title'))
    def __get_remaining_employment(self):
        return (self.employment.exclude(current=True)
                               .exclude(end_date__isnull=True)
                               .order_by('end_date', 'start_date',
                                         'company__name', 'title'))

    @classmethod
    def update_or_create_duplicate_check(cls, **kwargs):
        if 'email' in kwargs and kwargs['email']:
            person, _ = Person.objects.update_or_create(
                email=kwargs['email'], defaults=kwargs
            )
            return person
        elif 'linkedin_url' in kwargs and kwargs['linkedin_url']:
            person, _ = Person.objects.update_or_create(
                linkedin_url=kwargs['linkedin_url'], defaults=kwargs
            )
            return person
        else:
            return Person.objects.create(**kwargs)

    def get_latest_employment(self):
        try:
            current = self.__get_current_employment().last()
            if current:
                return current
            else:
                current = self.__get_null_employment().last()
                if current:
                    return current
                else:
                    return self.__get_remaining_employment().last()
        except Employment.DoesNotExist:
            return None

    def get_ordered_employment(self, reverse=False):
        current_employment = [e for e in self.__get_current_employment()]
        null_employment = [e for e in self.__get_null_employment()]
        remaining_employment = [e for e in self.__get_remaining_employment()]
        all_employment = (remaining_employment
                          + null_employment
                          + current_employment)
        return all_employment if not reverse else all_employment[::-1]

    def get_api_format(self):
        latest_employment = self.get_latest_employment()
        if latest_employment:
            (company, title) = (latest_employment.company.name,
                                latest_employment.title)
        else:
            (company, title) = (None, None)

        return {
            'id': self.id,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'name': self.full_name,
            'company': company,
            'title': title,
            'location': self.location,
            'email': self.email,
            'photoUrl': self.photo_url,
            'linkedinUrl': self.linkedin_url,
        }

    @classmethod
    def create_from_api(cls, request_json):
        """
        Expected request body:
        {
            'firstName': [required] [str],
            'lastName': [required] [str],
            'company': [str],
            'title': [str],
            'location': [str],
            'email': [str],
            'photoUrl': [str],
            'linkedinUrl': [str]
        }
        """
        person_dict = {}
        if request_json.get('firstName'):
            person_dict['first_name'] = request_json.get('firstName')
        if request_json.get('lastName'):
            person_dict['last_name'] = request_json.get('lastName')
        if request_json.get('location'):
            person_dict['location'] = request_json.get('location')
        if request_json.get('email'):
            person_dict['email'] = request_json.get('email')
        if request_json.get('photoUrl'):
            person_dict['photo_url'] = request_json.get('photoUrl')
        if request_json.get('linkedinUrl'):
            person_dict['linkedin_url'] = request_json.get('linkedinUrl')
        person = Person.update_or_create_duplicate_check(**person_dict)

        if request_json.get('company') and request_json.get('title'):
            company, _ = Company.objects.get_or_create(
                name=request_json.get('company')
            )
            # Don't create a new Employment object if
            # (person, company, title) already exists
            Employment.objects.get_or_create(
                person=person, company=company,
                title=request_json.get('title')
            )
        return person

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'firstName': [required] [str],
            'lastName': [required] [str],
            'location': [str],
            'email': [str],
            'photoUrl': [str],
            'linkedinUrl': [str]
        }
        """
        if request_json.get('firstName'):
            self.first_name = request_json.get('firstName')
        if request_json.get('lastName'):
            self.last_name = request_json.get('lastName')
        if request_json.get('location'):
            self.location = request_json.get('location')
        if request_json.get('email'):
            self.email = request_json.get('email')
        if request_json.get('photoUrl'):
            self.photo_url = request_json.get('photoUrl')
        if request_json.get('linkedinUrl'):
            self.linkedin_url = request_json.get('linkedinUrl')
        self.save()
        return self

    def get_api_experience(self):
        return [employment.get_api_format()
                for employment in self.get_ordered_employment(reverse=True)]

class PersonTag(models.Model):
    person     = models.ForeignKey(Person, related_name='tags')
    tag        = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Company(models.Model):
    name       = models.TextField(null=True, blank=True)
    location   = models.TextField(null=True, blank=True)
    website    = models.TextField(null=True, blank=True)
    logo_url   = models.TextField(null=True, blank=True)
    investor   = models.OneToOneField(Investor, unique=True, null=True,
                                      blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s' % self.name

    def get_employees(self, **kwargs):
        # Distinct on person id, sorted by end date and start date
        return self.employment.filter(**kwargs).order_by(
            'person__first_name', 'person__last_name',
            'end_date', 'start_date', 'person_id'
        ).distinct(
            'person__first_name', 'person__last_name',
            'end_date', 'start_date', 'person_id'
        )

    def get_board(self, **kwargs):
        # Distinct on person id, sorted by end date and start date
        return self.board_members.filter(**kwargs).order_by(
            'person__first_name', 'person__last_name',
            'end_date', 'start_date', 'person_id'
        ).distinct(
            'person__first_name', 'person__last_name',
            'end_date', 'start_date', 'person_id'
        )

    def get_investments(self, **kwargs):
        return self.investments.filter(**kwargs).order_by(
            'date', 'series'
        )

    def get_api_team(self, current=True):
        return [
            employee.person.get_api_format()
            for employee in self.get_employees(current=current)
        ]

    def get_api_board(self, current=True):
        return [
            board_member.person.get_api_format()
            for board_member in self.get_board()
        ]

    def get_api_investments(self):
        return [
            investment.get_api_format()
            for investment in self.get_investments()
        ]

class CompanyTag(models.Model):
    company    = models.ForeignKey(Company, related_name='tags')
    tag        = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Employment(models.Model):
    person     = models.ForeignKey(Person, related_name='employment')
    company    = models.ForeignKey(Company, related_name='employment')
    title      = models.TextField(null=True, blank=True)
    location   = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    current    = models.NullBooleanField(default=False)
    notes      = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s %s' % (unicode(self.person), unicode(self.company))

    def get_api_format(self):
        return {
            'id': self.id,
            'company': self.company.name,
            'title': self.title,
            'location': self.location,
            'startDate': self.start_date,
            'endDate': self.end_date,
            'notes': self.notes,
        }

    @classmethod
    def create_from_api(cls, person, request_json):
        """
        Expected request body:
        {
            'company': [required] [str],
            'title': [str],
            'location': [str],
            'startDate': [str],
            'endDate': [str],
            'notes': [str]
        }
        """
        company, _ = Company.objects.get_or_create(
            name=request_json.get('company')
        )

        employment_dict = {}
        if request_json.get('title'):
            employment_dict['title'] = request_json.get('title')
        if request_json.get('location'):
            employment_dict['location'] = request_json.get('location')
        if request_json.get('startDate'):
            employment_dict['start_date'] = parse_date(request_json.get('startDate'))
        if request_json.get('endDate'):
            employment_dict['end_date'] = parse_date(request_json.get('endDate'))
        if request_json.get('notes'):
            employment_dict['notes'] = request_json.get('notes')
        return Employment.objects.create(person=person, company=company,
                                         **employment_dict)

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'company': [str],
            'title': [str],
            'location': [str],
            'startDate': [str],
            'endDate': [str],
            'notes': [str]
        }
        """
        if request_json.get('company'):
            company, _ = Company.objects.get_or_create(
                name=request_json.get('company')
            )
            self.company = company
        if request_json.get('title'):
            self.title = request_json.get('title')
        if request_json.get('location'):
            self.location = request_json.get('location')
        if request_json.get('startDate'):
            self.start_date = parse_date(request_json.get('startDate'))
        if request_json.get('endDate'):
            self.end_date = parse_date(request_json.get('endDate'))
        if request_json.get('notes'):
            self.notes = request_json.get('notes')
        self.save()
        return self

class BoardMember(models.Model):
    person     = models.ForeignKey(Person, related_name='board_members')
    company    = models.ForeignKey(Company, related_name='board_members')
    location   = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    current    = models.NullBooleanField(default=True)
    notes      = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s %s' % (unicode(self.person), unicode(self.company))

    def get_api_format(self):
        latest_employment = self.get_latest_employment()
        if latest_employment:
            (company, title) = (latest_employment.company.name,
                                latest_employment.title)
        else:
            (company, title) = (None, None)

        return {
            'id': self.id,
            'company': company,
            'title': title,
            'location': self.location,
            'startDate': self.start_date,
            'endDate': self.end_date,
            'notes': self.notes,
        }

    @classmethod
    def create_from_api(cls, person, request_json):
        """
        Expected request body:
        {
            'company': [required] [str],
            'location': [str],
            'startDate': [str],
            'endDate': [str],
            'notes': [str]
        }
        """
        company, _ = Company.objects.get_or_create(
            name=request_json.get('company')
        )

        board_member_dict = {}
        if request_json.get('location'):
            board_member_dict['location'] = request_json.get('location')
        if request_json.get('startDate'):
            board_member_dict['start_date'] = parse_date(request_json.get('startDate'))
        if request_json.get('endDate'):
            board_member_dict['end_date'] = parse_date(request_json.get('endDate'))
        if request_json.get('notes'):
            board_member_dict['notes'] = request_json.get('notes')
        return BoardMember.objects.create(person=person, company=company,
                                          **board_member_dict)

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'company': [str],
            'location': [str],
            'startDate': [str],
            'endDate': [str],
            'notes': [str]
        }
        """
        if request_json.get('company'):
            company, _ = Company.objects.get_or_create(
                name=request_json.get('company')
            )
            self.company = company
        if request_json.get('location'):
            self.location = request_json.get('location')
        if request_json.get('startDate'):
            self.start_date = parse_date(request_json.get('startDate'))
        if request_json.get('endDate'):
            self.end_date = parse_date(request_json.get('endDate'))
        if request_json.get('notes'):
            self.notes = request_json.get('notes')
        self.save()
        return self

class Investment(models.Model):
    company    = models.ForeignKey(Company, related_name='investments')
    series     = models.CharField(max_length=25)
    date       = models.DateField(null=True, blank=True)
    pre_money  = models.DecimalField(max_digits=24, decimal_places=6,
                                     null=True, blank=True)
    raised     = models.DecimalField(max_digits=24, decimal_places=6,
                                     null=True, blank=True)
    post_money = models.DecimalField(max_digits=24, decimal_places=6,
                                     null=True, blank=True)
    share_price         = models.DecimalField(max_digits=24, decimal_places=6,
                                              null=True, blank=True)
    preference_multiple = models.FloatField(null=True, blank=True)
    preference_dollars  = models.DecimalField(max_digits=24, decimal_places=6,
                                              null=True, blank=True)
    conversion_ratio    = models.FloatField(null=True, blank=True)
    seniority           = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'series')

    def __unicode__(self):
        return u'%s %s' % (unicode(self.company), self.series)

    def get_api_format(self):
        return {
            'id': self.id,
            'company': self.company.name,
            'series': self.series,
            'date': self.date,
            'preMoney': self.pre_money,
            'raised': self.raised,
            'postMoney': self.post_money,
            'sharePrice': self.share_price,
        }

    @classmethod
    def create_from_api(cls, company, request_json):
        """
        Expected request body:
        {
            'series': [required] [str],
            'date': [datetime.date],
            'preMoney': [float],
            'raised': [float],
            'postMoney': [float],
            'sharePrice': [float]
        }
        """
        # Should not get to "No Series Name" because of validation
        series = request_json.get('series') or 'No Series Name'

        investment_dict = {}
        if request_json.get('date'):
            investment_dict['date'] = parse_date(request_json.get('date'))
        if request_json.get('preMoney'):
            investment_dict['pre_money'] = request_json.get('preMoney')
        if request_json.get('raised'):
            investment_dict['raised'] = request_json.get('raised')
        if request_json.get('postMoney'):
            investment_dict['post_money'] = request_json.get('postMoney')
        if request_json.get('sharePrice'):
            investment_dict['share_price'] = request_json.get('sharePrice')
        investment, _ = Investment.objects.update_or_create(
            company=company, series=series, defaults=investment_dict
        )
        return investment

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'series': [str],
            'date': [datetime.date],
            'preMoney': [float],
            'raised': [float],
            'postMoney': [float],
            'sharePrice': [float]
        }
        """
        if request_json.get('series'):
            self.series = request_json.get('series')
        if request_json.get('date'):
            self.date = parse_date(request_json.get('date'))
        if request_json.get('preMoney'):
            self.pre_money = request_json.get('preMoney')
        if request_json.get('raised'):
            self.raised = request_json.get('raised')
        if request_json.get('postMoney'):
            self.post_money = request_json.get('postMoney')
        if request_json.get('sharePrice'):
            self.share_price = request_json.get('sharePrice')
        self.save()
        # TODO: Catch duplicate series name error
        return self

class InvestorInvestment(models.Model):
    investment = models.ForeignKey(Investment,
                                   related_name='investor_investments',
                                   on_delete=models.CASCADE)
    investor   = models.ForeignKey(Investor,
                                   related_name='investor_investments',
                                   on_delete=models.PROTECT)
    date       = models.DateField(null=True, blank=True)
    lead       = models.NullBooleanField()
    ownership  = models.FloatField(null=True, blank=True) # Fully diluted
    invested   = models.DecimalField(max_digits=24, decimal_places=6,
                                     null=True, blank=True)
    shares     = models.DecimalField(max_digits=24, decimal_places=6,
                                     null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('investment', 'investor', 'date'))

