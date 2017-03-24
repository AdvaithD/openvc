"""
Models:

* Person
** PersonTag

* Company
** CompanyTag
** Metric
*** MetricValue
** Investment
*** InvestorInvestment

* Investor

* Employment
* BoardMember

* Deal
"""

import datetime
import json
from decimal import Decimal
from django.db import models
from shared.utils import parse_date

DEFAULT_ACCOUNT_ID = 1 # Can't define this in users.models due to circular
                       # imports.

def create_defaults_hash(api_response, api_field_map):
    """
    Creates a formatted dictionary from the API response that is mapped to the
    expected API fields. Only includes non-null API response values.
    Args:
        api_response [dict]: {
            [API field name]: [API field value],
            ...
        },
        api_field_map [dict]: {
            [Internal model field name]: [API field name],
            ...
        }
    Returns:
        [dict]: {
            [Internal model field name]: [API field value]
        }
    """
    def is_null(value):
        return value is None or value == '' or value == 'None'

    return {
        internal_field: api_response[api_field]
        for internal_field, api_field in api_field_map.iteritems()
        if api_field in api_response and not is_null(api_response[api_field])
    }

class Person(models.Model):
    """
    Relationships:
        Investor (1:1)
        PersonTag (1:N)
        Employment (1:N)
        BoardMember (1:N)
    Candidate key:
        None
    Required fields:
        account, first_name, last_name
    """

    def _get_full_name(self):
        names = [n for n in [self.first_name, self.last_name] if n]
        return ' '.join(names)

    account    = models.ForeignKey('users.Account', related_name='people',
                                   default=DEFAULT_ACCOUNT_ID)

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    full_name = property(_get_full_name)

    def __unicode__(self):
        return u'%s: %s' % (unicode(self.account), self.full_name)

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
    def update_or_create_duplicate_check(cls, account, **kwargs):
        if 'email' in kwargs and kwargs['email']:
            person, _ = Person.objects.update_or_create(
                account=account, email=kwargs['email'], defaults=kwargs
            )
            return person
        elif 'linkedin_url' in kwargs and kwargs['linkedin_url']:
            person, _ = Person.objects.update_or_create(
                account=account, linkedin_url=kwargs['linkedin_url'],
                defaults=kwargs
            )
            return person
        else:
            return Person.objects.create(account=account, **kwargs)

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
    def create_from_api(cls, account, request_json):
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
        person = Person.update_or_create_duplicate_check(account,
                                                         **person_dict)

        if request_json.get('company') and request_json.get('title'):
            company, _ = Company.objects.get_or_create(
                account=account, name=request_json.get('company')
            )
            # Don't create a new Employment object if
            # (person, company, title) already exists
            Employment.objects.get_or_create(
                account=account, person=person, company=company,
                title=request_json.get('title')
            )
        return person

    def update_from_api(self, request_json):
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
    """
    Relationships:
        Person (N:1)
    Candidate key:
        (account_id, person_id, tag)
    Required fields:
        account, person, tag
    """

    account    = models.ForeignKey('users.Account', related_name='person_tags',
                                   default=DEFAULT_ACCOUNT_ID)

    person     = models.ForeignKey(Person, related_name='tags')
    tag        = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('account', 'person', 'tag')

    def __unicode__(self):
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.person),
                                self.tag))

class Company(models.Model):
    """
    Relationships:
        Investor (1:1)
        CompanyTag (1:N)
        Employment (1:N)
        BoardMember (1:N)
        Metric (1:N)
        Investment (1:N)
        Deal (1:N)
    Candidate key:
        None
    Required fields:
        account, name
    """

    account    = models.ForeignKey('users.Account', related_name='companies',
                                   default=DEFAULT_ACCOUNT_ID)

    name       = models.TextField()
    location   = models.TextField(null=True, blank=True)
    website    = models.TextField(null=True, blank=True)
    segment    = models.TextField(null=True, blank=True)
    sector     = models.TextField(null=True, blank=True)
    logo_url   = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    crunchbase_id        = models.TextField(unique=True, null=True, blank=True)
    crunchbase_permalink = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s: %s' % (unicode(self.account), self.name or u'')

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
        return self.investments.filter(**kwargs).order_by('date', 'series')

    def get_first_investment(self, investor=None):
        kwargs = ({} if investor is None else
                  { 'investor_investments__investor': investor })
        return self.get_investments(**kwargs).first()

    def get_latest_investment(self, investor=None):
        kwargs = ({} if investor is None else
                  { 'investor_investments__investor': investor })
        return self.get_investments(**kwargs).last()

    def get_metrics(self, **kwargs):
        return self.metrics.filter(**kwargs).order_by('name')

    # Company API

    def get_api_format(self):
        return {
            'id': self.id,
            'name': self.name,
            'segment': self.segment,
            'sector': self.sector,
            'location': self.location,
            'website': self.website,
            'logoUrl': self.logo_url,
        }

    @classmethod
    def create_from_api(cls, account, request_json):
        """
        Expected request body:
        {
            'name': [required] [str],
            'segment': [str],
            'sector': [str],
            'location': [str],
            'logoUrl': [str],
            'website': [str]
        }
        """
        company_dict = {}
        if request_json.get('name'):
            company_dict['name'] = request_json.get('name')
        if request_json.get('segment'):
            company_dict['segment'] = request_json.get('segment')
        if request_json.get('sector'):
            company_dict['sector'] = request_json.get('sector')
        if request_json.get('location'):
            company_dict['location'] = request_json.get('location')
        if request_json.get('logoUrl'):
            company_dict['logo_url'] = request_json.get('logoUrl')
        if request_json.get('website'):
            company_dict['website'] = request_json.get('website')
        return Company.objects.create(account=account, **company_dict)

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'name': [str],
            'segment': [str],
            'sector': [str],
            'location': [str],
            'logoUrl': [str],
            'website': [str]
        }
        """
        if request_json.get('name'):
            self.name = request_json.get('name')
        if request_json.get('segment'):
            self.segment = request_json.get('segment')
        if request_json.get('sector'):
            self.sector = request_json.get('sector')
        if request_json.get('location'):
            self.location = request_json.get('location')
        if request_json.get('logoUrl'):
            self.logo_url = request_json.get('logoUrl')
        if request_json.get('website'):
            self.website = request_json.get('website')

        self.save()
        return self

    # Startup API

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

    def get_api_metrics(self):
        return [
            metric.get_api_list_format()
            for metric in self.get_metrics()
        ]

    # Investor API

    def get_last_metric(self, metric_name):
        try:
            return (self.metrics.get(name=metric_name, interval='Quarter',
                                     estimated=False)
                                .metric_values
                                .order_by('date').last())
        except Metric.DoesNotExist:
            return None

    def get_api_portco_format(self, investor):
        first_investment = self.get_latest_investment(investor)
        if first_investment:
            (first_series, first_date, first_raised, first_post) = \
                (first_investment.series, first_investment.date,
                 first_investment.raised, first_investment.post_money)
        else:
            (first_series, first_date, first_raised, first_post) = \
                (None, None, None, None)

        last_investment = self.get_latest_investment()
        if last_investment:
            (last_series, last_date, last_raised, last_post) = \
                (last_investment.series, last_investment.date,
                 last_investment.raised, last_investment.post_money)
        else:
            (last_series, last_date, last_raised, last_post) = \
                (None, None, None, None)

        revenue = self.get_last_metric('Revenue')
        revenue = revenue.get_api_format() if revenue else {}
        burn = self.get_last_metric('Burn')
        burn = burn.get_api_format() if burn else {}
        cash = self.get_last_metric('Cash')
        cash = cash.get_api_format() if cash else {}
        headcount = self.get_last_metric('Headcount')
        headcount = headcount.get_api_format() if headcount else {}

        return {
            'id': self.id,
            'name': self.name,
            'segment': self.segment,
            'sector': self.sector,
            'location': self.location,
            'website': self.website,
            'logoUrl': self.logo_url,
            'totalRaised': self.get_total_raised(),
            'invested': investor.get_total_investment(self),
            'ownership': investor.get_current_ownership(self),
            'latestRoundSeries': last_series,
            'lastRound': {
                'series': last_series,
                'date': last_date,
                'raised': last_raised,
                'postMoney': last_post,
            },
            'firstRound': {
                'series': first_series,
                'date': first_date,
                'raised': first_raised,
                'postMoney': first_post,
            },
            'lastMetrics': {
                'revenue': revenue,
                'burn': burn,
                'cash': cash,
                'headcount': headcount,
            },
            'board': self.get_api_board(),
            'interactions': investor.company.account.get_company_interactions(self),
        }

    # Startup data

    def get_total_raised(self, **kwargs):
        return (self.investments.filter(**kwargs)
                                .aggregate(total=models.Sum('raised'))['total']
                or Decimal(0))

class CompanyTag(models.Model):
    """
    Relationships:
        Company (N:1)
    Candidate key:
        (account_id, company_id, tag)
    Required fields:
        account, company, tag
    """

    account    = models.ForeignKey('users.Account', related_name='company_tags',
                                   default=DEFAULT_ACCOUNT_ID)

    company    = models.ForeignKey(Company, related_name='tags')
    tag        = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('account', 'company', 'tag')

    def __unicode__(self):
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.company),
                                self.tag))

class Investor(models.Model):
    """
    Relationships:
        Person (1:1)
        Company (1:1)
    Candidate key:
        (account_id, person_id), (account_id, company_id)
    Required fields:
        account, name, type
    """

    TYPES = {
        'Company': 'COMPANY',
        'Person': 'PERSON',
    }
    TYPE_CHOICES = [(v, k) for k, v in TYPES.iteritems()]

    account    = models.ForeignKey('users.Account', related_name='investors',
                                   default=DEFAULT_ACCOUNT_ID)

    name       = models.TextField()
    type       = models.TextField(choices=TYPE_CHOICES, default='COMPANY')
    person     = models.OneToOneField(Person, unique=True, null=True,
                                      blank=True, on_delete=models.CASCADE)
    company    = models.OneToOneField(Company, unique=True, null=True,
                                      blank=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('account', 'person'), ('account', 'company'))

    def __unicode__(self):
        return u'%s: %s' % (unicode(self.account), self.name)

    def get_total_investment(self, company, **kwargs):
        args = { 'investor': self, 'investment__company': company }
        args.update(kwargs)
        return (InvestorInvestment.objects.filter(**args)
                                  .aggregate(total=models.Sum('invested'))['total']
                or Decimal(0))

    def get_current_ownership(self, company, **kwargs):
        args = { 'investor': self, 'investment__company': company }
        args.update(kwargs)

        # Get the most recent ownership % (each round has current total own %)
        for ii in InvestorInvestment.objects.filter(**args).order_by('-date'):
            if ii.ownership:
                return ii.ownership
        return None

class Employment(models.Model):
    """
    Relationships:
        Person (N:1)
        Company (N:1)
    Candidate key:
        None. NOT: (account_id, person_id, company_id) in case the title,
        location, or something else changes.
    Required fields:
        account, person, company
    """

    account    = models.ForeignKey('users.Account', related_name='employments',
                                   default=DEFAULT_ACCOUNT_ID)

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
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.person),
                                unicode(self.company)))

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
    def create_from_api(cls, account, person, request_json):
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
            account=account, name=request_json.get('company')
        )

        employment_dict = {}
        if request_json.get('title'):
            employment_dict['title'] = request_json.get('title')
        if request_json.get('location'):
            employment_dict['location'] = request_json.get('location')
        if request_json.get('startDate'):
            employment_dict['start_date'] = parse_date(
                request_json.get('startDate')
            )
        if request_json.get('endDate'):
            employment_dict['end_date'] = parse_date(
                request_json.get('endDate')
            )
        if request_json.get('notes'):
            employment_dict['notes'] = request_json.get('notes')
        return Employment.objects.create(account=account, person=person,
                                         company=company, **employment_dict)

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
            # TODO: Change this + add account reference
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
    """
    Relationships:
        Person (N:1)
        Company (N:1)
    Candidate key:
        None. NOT: (account_id, person_id, company_id) so a board member can
        leave a company and come back. There should be a constraint that
        (account_id, person_id, company_id, current=True) is unique.
    Required fields:
        account, person, company
    """

    account    = models.ForeignKey('users.Account',
                                   related_name='board_members',
                                   default=DEFAULT_ACCOUNT_ID)

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
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.person),
                                unicode(self.company)))

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
    def create_from_api(cls, account, person, request_json):
        """
        CURRENTLY UNUSED?

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
            account=account, name=request_json.get('company')
        )

        board_member_dict = {}
        if request_json.get('location'):
            board_member_dict['location'] = request_json.get('location')
        if request_json.get('startDate'):
            board_member_dict['start_date'] = parse_date(
                request_json.get('startDate')
            )
        if request_json.get('endDate'):
            board_member_dict['end_date'] = parse_date(
                request_json.get('endDate')
            )
        if request_json.get('notes'):
            board_member_dict['notes'] = request_json.get('notes')
        return BoardMember.objects.create(account=account, person=person,
                                          company=company, **board_member_dict)

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
            # TODO: Change this + add account reference
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

class Metric(models.Model):
    """
    interval [text]: Metric tracking interval (e.g. Quarterly for Quarterly Net
                     Revenue).
    estimated [bool]: True if the metric is a projection, False otherwise.

    Relationships:
        Company (N:1)
        MetricValue (1:N)
    Candidate key:
        (account_id, company_id, name, interval, estimated)
    Required fields:
        account, company, name
    """

    account    = models.ForeignKey('users.Account', related_name='metrics',
                                   default=DEFAULT_ACCOUNT_ID)

    company    = models.ForeignKey(Company, related_name='metrics')
    name       = models.TextField()
    description = models.TextField(null=True, blank=True)
    interval   = models.TextField(default='Quarter', null=True, blank=True)
    estimated  = models.NullBooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('account', 'company', 'name', 'interval',
                           'estimated')


    def __unicode__(self):
        return (u'%s: %s %s %s %s' % (unicode(self.account),
                                      unicode(self.company), self.name,
                                      self.interval, self.estimated))

    def get_api_format(self):
        return [
            metric_value.get_api_format()
            for metric_value in self.metric_values.order_by('date')
        ]

    def get_api_list_format(self):
        metric_dict = {
            'id': self.id,
            'company': self.company.name,
            'metric': self.name,
        }
        for metric_value in self.metric_values.order_by('date'):
            metric_dict[metric_value.date.strftime('%Y-%m-%d')] = \
                metric_value.value
        return metric_dict

    @classmethod
    def create_from_api(cls, account, company, request_json):
        """
        Expected request body:
        {
            'metric': [required] [str],
            [datestring]: [float],
            [datestring]: [float],
            [datestring]: [float],
            ...
        }
        """
        metric_name = request_json.get('metric')
        metric, _ = Metric.objects.update_or_create(
            account=account, company=company, name=metric_name,
            estimated=False, interval='Quarter'
        )
        for k, v in request_json.iteritems():
            try:
                date = datetime.datetime.strptime(k, '%Y-%m-%d').date()
                if date and v:
                    MetricValue.objects.update_or_create(
                        account=account, metric=metric, date=date,
                        defaults={ 'value': v }
                    )
            except ValueError:
                continue

        return metric

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'metric': [required] [str],
            [datestring]: [float],
            [datestring]: [float],
            [datestring]: [float],
            ...
        }
        """
        for k, v in request_json.iteritems():
            try:
                date = datetime.datetime.strptime(k, '%Y-%m-%d').date()
                if date and v:
                    MetricValue.objects.update_or_create(
                        metric=self,
                        date=date,
                        defaults={ 'value': v }
                    )
            except ValueError:
                continue

        return self

class MetricValue(models.Model):
    """
    Relationships:
        Metric (N:1)
    Candidate key:
        (account_id, metric_id, date)
    Required fields:
        account, metric, date, value
    """

    account    = models.ForeignKey('users.Account',
                                   related_name='metric_values',
                                   default=DEFAULT_ACCOUNT_ID)

    metric     = models.ForeignKey(Metric, related_name='metric_values')
    date       = models.DateField()
    value      = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('account', 'metric', 'date')

    def __unicode__(self):
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.metric),
                                self.date))

    def get_api_format(self):
        return {
            'id': self.id,
            'company': self.metric.company.name,
            'name': self.metric.name,
            'date': self.date,
            'interval': self.metric.interval,
            'estimated': self.metric.estimated,
            'value': self.value,
        }

class Investment(models.Model):
    """
    Relationships:
        Company (N:1)
        InvestorInvestment (1:N)
    Candidate key:
        (account_id, company_id, series)
    Required fields:
        account, company, series
    """

    account    = models.ForeignKey('users.Account', related_name='investments',
                                   default=DEFAULT_ACCOUNT_ID)

    company    = models.ForeignKey(Company, related_name='investments')
    series     = models.TextField()
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
        unique_together = ('account', 'company', 'series')

    def __unicode__(self):
        return (u'%s: %s %s' % (unicode(self.account), unicode(self.company),
                                self.series))

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
    def create_from_api(cls, account, company, request_json):
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
            account=account, company=company, series=series,
            defaults=investment_dict
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

    def get_api_investors(self):
        return [investor_investment.get_api_format()
                for investor_investment
                in self.investor_investments.order_by(
                    'investment__date', 'investment__series', 'date',
                    'investor__name'
                )]

class InvestorInvestment(models.Model):
    """
    Relationships:
        Investment (N:1)
        Investor (N:1)
    Candidate key:
        (account_id, investment_id, investor_id)
    Required fields:
        account, investment, investor
    """

    account    = models.ForeignKey('users.Account',
                                   related_name='investor_investments',
                                   default=DEFAULT_ACCOUNT_ID)

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
        unique_together = ('account', 'investment', 'investor')

    def __unicode__(self):
        return (u'%s: %s %s %s' % (unicode(self.account),
                                   unicode(self.investment),
                                   unicode(self.investor)))

    def get_api_format(self):
        return {
            'id': self.id,
            'investmentId': self.investment.id,
            'company': self.investment.company.name,
            'series': self.investment.series,
            'investor': self.investor.name,
            'investorType': self.investor.type,
            'date': self.investment.date,
            'preMoney': self.investment.pre_money,
            'raised': self.investment.raised,
            'postMoney': self.investment.post_money,
            'sharePrice': self.investment.share_price,
            'invested': self.invested,
            'ownership': self.ownership,
            'shares': self.shares,
        }

    @classmethod
    def create_from_api(cls, account, investment, request_json):
        """
        Expected request body:
        {
            'investor': [required] [str],
            'investorType': [str],
            'invested': [float],
            'ownership': [float],
            'shares': [float]
        }
        """
        investor_dict = {}
        if request_json.get('investorType'):
            investor_dict['investor_type'] = request_json.get('investorType')
        investor, _ = Investor.objects.get_or_create(
            account=account, name=request_json.get('investor'),
            defaults=investor_dict
        )

        investor_investment_dict = {}
        if request_json.get('invested'):
            investor_investment_dict['invested'] = request_json.get('invested')
        if request_json.get('ownership'):
            investor_investment_dict['ownership'] = request_json.get('ownership')
        if request_json.get('shares'):
            investor_investment_dict['shares'] = request_json.get('shares')
        investor_investment, _ = InvestorInvestment.objects.update_or_create(
            account=account, investment=investment, investor=investor,
            defaults=investor_investment_dict
        )
        return investor_investment

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'investor': [str],
            'investorType': [str],
            'invested': [float],
            'ownership': [float],
            'shares': [float]
        }
        """
        investor_dict = {}
        if request_json.get('investor') and request_json.get('investorType'):
            # TODO: Change this + add account reference
            investor, _ = Investor.objects.get_or_create(
                name=request_json.get('investor'),
                defaults=investor_dict
            )

        if request_json.get('invested'):
            self.invested = request_json.get('invested')
        if request_json.get('ownership'):
            self.ownership = request_json.get('ownership')
        if request_json.get('shares'):
            self.shares = request_json.get('shares')
        self.save()
        return self

class Deal(models.Model):
    """
    Relationships:
        Company (N:1)
        Investment (1:1)
        Person (referrer) (N:1)
        Person (owner) (N:1) # TODO: Consider changing to User model
    Candidate key:
        None. Can have multiple deals for each (account, company) tuple
        (multiple rounds of fundraising).
    Required fields:
        account, company, investor
    """

    account    = models.ForeignKey('users.Account', related_name='deals',
                                   default=DEFAULT_ACCOUNT_ID)

    name       = models.TextField()
    company    = models.ForeignKey(Company, related_name='deals',
                                   null=True, blank=True,
                                   on_delete=models.CASCADE)
    investment = models.OneToOneField(Investment, null=True, blank=True,
                                      on_delete=models.SET_NULL)
    referrer   = models.ForeignKey(Person, related_name='referrer_deals',
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL)
    owner      = models.ForeignKey(Person, related_name='owner_deals',
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL)
    date       = models.DateField(null=True, blank=True)
    source     = models.TextField(null=True, blank=True)
    type       = models.TextField(null=True, blank=True)
    status     = models.TextField(null=True, blank=True)
    stage      = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return u'%s: %s' % (unicode(self.account), self.name)

    def get_api_format(self):
        return {
            'id': self.id,
            'name': self.name,
            'company': self.company.name if self.company else None,
            'companyId': self.company.id if self.company else None,
            'investment': self.investment.series if self.investment else None,
            'investmentId': self.investment.id if self.investment else None,
            'referrer': self.referrer.full_name if self.referrer else None,
            'referrerId': self.referrer.id if self.referrer else None,
            'owner': self.owner.full_name if self.owner else None,
            'ownerId': self.owner.id if self.owner else None,
            'date': self.date,
            'source': self.source,
            'type': self.type,
            'status': self.status,
            'stage': self.stage,
        }

    @classmethod
    def create_from_api(cls, account, request_json):
        """
        Expected request body:
        {
            'companyId': [int],
            'investmentId': [int],
            'name': [required] [string],
            'referrerId': [int],
            'ownerId': [int],
            'date': [datetime.date],
            'source': [float],
            'type': [float],
            'status': [float],
            'stage': [float]
        }
        """
        # TODO: Foreign key relationships
        deal_dict = { 'name': request_json.get('name') }

        if request_json.get('date'):
            deal_dict['date'] = parse_date(request_json.get('date'))
        if request_json.get('source'):
            deal_dict['source'] = request_json.get('source')
        if request_json.get('type'):
            deal_dict['type'] = request_json.get('type')
        if request_json.get('status'):
            deal_dict['status'] = request_json.get('status')
        if request_json.get('stage'):
            deal_dict['stage'] = request_json.get('stage')
        deal = Deal.objects.create(account=account, **deal_dict)
        return deal

    def update_from_api(self, request_json):
        """
        Expected request body:
        {
            'companyId': [int],
            'investmentId': [int],
            'name': [string],
            'referrerId': [int],
            'ownerId': [int],
            'date': [datetime.date],
            'source': [float],
            'type': [float],
            'status': [float],
            'stage': [float]
        }
        """
        # TODO: Foreign key relationships
        if request_json.get('name'):
            self.name = request_json.get('name')
        if request_json.get('date'):
            self.date = parse_date(request_json.get('date'))
        if request_json.get('source'):
            self.source = request_json.get('source')
        if request_json.get('type'):
            self.type = request_json.get('type')
        if request_json.get('status'):
            self.status = request_json.get('status')
        if request_json.get('stage'):
            self.stage = request_json.get('stage')
        self.save()
        return self

