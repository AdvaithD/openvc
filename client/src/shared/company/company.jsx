import React from 'react';
import Immutable from 'immutable';
import {authFetch, preprocessJSON} from '../../utils/api.js';
import moment from 'moment';

import LinkWrapper from '../../components/link.jsx';
import {CreateTeamMemberModal,
        CreateBoardMemberModal} from '../../components/modals/person.jsx';
import EditTable from '../../components/edittable/edittable.jsx';

import './company.scss';

/*
 * props:
 *   API_URL [string]: Backend API endpoint to hit.
 *   CREATE_HEADLINE [string]: Modal title.
 *   UPDATE_HEADLINE [string]: Modal "add existing member" section title.
 *   USER_TYPE [string]: 'founder' or 'investor', depending on user role.
 */
class MemberSection extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      members: [],
      modalVisible: false
    };

    // New member component handlers
    this.addNewMember = this.addNewMember.bind(this);
    this.handleDeleteMember = this.handleDeleteMember.bind(this);

    // New member modal handlers
    this.cancelNewMember = this.cancelNewMember.bind(this);

    // Update existing member component handlers
    this.updateInput = this.updateInput.bind(this);
    this.cancelEdits = this.cancelEdits.bind(this);
    this.editMember = this.editMember.bind(this);
    this.handleUpdateMember = this.handleUpdateMember.bind(this);

    // Member API
    this.getMemberList = this.getMemberList.bind(this);
    this.createMember = this.createMember.bind(this);
    this.updateMember = this.updateMember.bind(this);
    this.deleteMember = this.deleteMember.bind(this);

    this.getMemberList();
  }

  /*
   * New member component handlers
   */

  addNewMember(e) {
    this.setState({ modalVisible: true });
  }

  cancelNewMember(e) {
    this.setState({ modalVisible: false });
  }

  /*
   * New member modal handlers
   */

  handleDeleteMember(e) {
    e.stopPropagation();
    this.deleteMember(Number(e.currentTarget.id));
  }

  /*
   * Update existing member component handlers
   */

  updateInput(e) {
    const memberId = Number(e.currentTarget.id);
    const memberIdx = this.state.members.findIndex(member =>
      member.id === memberId
    );
    const fieldName = e.target.name;
    const fieldValue = e.target.value;
    const newState = Immutable.fromJS(this.state)
      .updateIn(['members', memberIdx, fieldName], value => fieldValue);
    this.setState(newState.toJS());
  }

  cancelEdits() {
    /* Get user out of edit mode for existing cards */
    const newState = Immutable.fromJS(this.state)
      .update('members', members =>
        members.map(member => member.set('editing', false))
      );
    this.setState(newState.toJS());
  }

  editMember(e) {
    e.stopPropagation();
    const memberId = Number(e.currentTarget.id);
    const memberIdx = this.state.members.findIndex(member =>
      member.id === memberId
    );
    const newState = Immutable.fromJS(this.state)
      .update('members', members =>
        members.map((member, index) => {
          if (index === memberIdx)
            return member.set('editing', true);
          else
            return member.set('editing', false);
          })
        );
    this.setState(newState.toJS());
  }

  handleUpdateMember(e) {
    const memberId = Number(e.currentTarget.id);
    const memberIdx = this.state.members.findIndex(member =>
      member.id === memberId
    );
    const member = this.state.members[memberIdx];
    this.updateMember(memberId, {
      firstName: member.firstName,
      lastName: member.lastName,
      title: member.title,
      email: member.email,
      linkedinUrl: member.linkedinUrl
    });
  }

  /*
   * Member API
   */

  getMemberList() {
    authFetch(this.props.API_URL)
      .then(function(response) {
        if (response.ok) {
          return response.json();
        }
        else {
          return response.json().then(json => {
            throw new Error(json);
          });
        }
      })
      .then(json => {
        json = preprocessJSON(json);
        this.setState({ members: json });
      })
      .catch(err => {
        // Failure
        console.log(err);
        return err;
      });
  }

  createMember(member) {
    authFetch(this.props.API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(member)
    })
    .then(function(response) {
      if (response.ok) {
        return response.json();
      }
      else {
        return response.json().then(json => {
          throw new Error(json);
        });
      }
    })
    .then(json => {
      // Success
      json = preprocessJSON(json);
      const newState = Immutable.fromJS(this.state)
        .update('members', members => members.push(json));

      this.setState(newState.toJS());
    })
    .catch(err => {
      // Failure
      console.log(err);
      return err;
    });
  }

  updateMember(memberId, member) {
    authFetch(`${this.props.API_URL}/${memberId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(member)
    })
    .then(function(response) {
      if (response.ok) {
        return response.json();
      }
      else {
        return response.json().then(json => {
          // TODO: Handle error responses
          throw new Error(json);
        });
      }
    })
    .then(json => {
      // Success
      json = preprocessJSON(json);
      const memberIdx = this.state.members.findIndex(member =>
        member.id === json.id
      );

      // If an existing member was updated
      if (memberIdx > -1) {
        const newState = Immutable.fromJS(this.state)
          .setIn(['members', memberIdx], json);
        this.setState(newState.toJS());
      }
      // If an existing contact was added as a member
      else {
        const newState = Immutable.fromJS(this.state)
          .update('members', members => members.push(json));
        this.setState(newState.toJS());
      }
    })
    .catch(err => {
      // Failure
      console.log(err);
      return err;
    });
  }

  deleteMember(memberId) {
    authFetch(`${this.props.API_URL}/${memberId}`, {
      method: 'DELETE'
    })
    .then(function(response) {
      if (response.ok) {
        return response.json();
      }
      else {
        return response.json().then(json => {
          throw new Error(json);
        });
      }
    })
    .then(json => {
      // Success
      json = preprocessJSON(json);
      const deletedId = json.id;
      const newMembers = this.state.members.filter(member =>
        member.id !== deletedId
      );
      const newState = Immutable.fromJS(this.state)
        .set('members', newMembers);

      this.setState(newState.toJS());
    })
    .catch(err => {
      // Failure
      console.log(err);
      return err;
    });
  }

  render() {
    const CreateMemberModal = this.props.createMemberModal;

    const members = this.state.members.map((member, index) => {
      if (member.editing) {
        return (
          <div className="ovc-member-card edit" key={member.id}>
            <input type="text" name="firstName" id={member.id}
                   value={member.firstName} onChange={this.updateInput}
                   placeholder="First name, e.g. John" />
            <input type="text" name="lastName" id={member.id}
                   value={member.lastName} onChange={this.updateInput}
                   placeholder="Last name, e.g. Doe" />
            <input type="text" name="title" id={member.id}
                   value={member.title} onChange={this.updateInput}
                   placeholder="Title, e.g. CEO" />
            <input type="text" name="email" id={member.id}
                   value={member.email} onChange={this.updateInput}
                   placeholder="Email, e.g. john.doe@gmail.com" />
            <input type="text" name="photoUrl" id={member.id}
                   value={member.photoUrl} onChange={this.updateInput}
                   placeholder="Image URL, http://..." />
            <i className="ion-ios-close-outline cancel" id={member.id}
                 onClick={this.cancelEdits} />
            <i className="ion-ios-checkmark-outline save" id={member.id}
                 onClick={this.handleUpdateMember} />
          </div>
        );
      }
      else {
        return (
          <LinkWrapper to={`/${this.props.USER_TYPE}/contacts/${member.id}`}
                key={member.id}>
            <div className="ovc-member-card item">
              <i className="ion-trash-a remove-member" id={member.id}
                 onClick={this.handleDeleteMember} />
              <i className="ion-edit edit-member" id={member.id}
                 onClick={this.editMember} />
              <img src={member.photoUrl} />
              <div>{member.firstName} {member.lastName}</div>
              <div>{member.title}</div>
              <div>{member.email}</div>
            </div>
          </LinkWrapper>
        );
      }
    });

    return (
      <div className="ovc-member-section">
        {members}
        <div className="ovc-member-card add" onClick={this.addNewMember}>
          <i className="ion-ios-plus-empty" />
        </div>
        <CreateMemberModal visible={this.state.modalVisible}
                           hideModal={this.cancelNewMember}
                           createEntity={this.createMember}
                           updateEntity={this.updateMember} />
      </div>
    );
  }
}

class TeamSection extends React.Component {
  render() {
    return <MemberSection API_URL={`${this.props.API_URL_BASE}/team`}
                          createMemberModal={CreateTeamMemberModal}
                          {...this.props} />
  }
}

class BoardSection extends React.Component {
  render() {
    return <MemberSection API_URL={`${this.props.API_URL_BASE}/board`}
                          createMemberModal={CreateBoardMemberModal}
                          {...this.props} />
  }
}

class InvestmentSection extends React.Component {
  constructor(props) {
    super(props);

    this.FIELDS = ['series', 'date', 'preMoney', 'raised', 'postMoney',
                   'sharePrice'];
    this.FIELD_MAP = {
      series: {
        display: 'Round',
        type: 'string',
        required: true
      },
      date: {
        display: 'Date',
        type: 'date',
        required: false
      },
      preMoney: {
        display: 'Pre Money Val',
        type: 'money',
        required: false
      },
      raised: {
        display: 'Amount Raised',
        type: 'money',
        required: false
      },
      postMoney: {
        display: 'Post Money Val',
        type: 'money',
        required: false
      },
      sharePrice: {
        display: 'Price Per Share',
        type: 'money',
        required: false
      }
    };
  }

  render() {
    return (
      <div className="ovc-edit-table-container">
        <EditTable API_URL={`${this.props.API_URL_BASE}/investments`}
                   FIELDS={this.FIELDS}
                   FIELD_MAP={this.FIELD_MAP}
                   {...this.props} />
      </div>
    );
  }
}

class InvestorSection extends React.Component {
  constructor(props) {
    super(props);

    this.FIELDS = ['investor', 'investorType', 'date', 'preMoney',
                   'raised', 'postMoney', 'sharePrice', 'invested',
                   'ownership', 'shares'];
    this.FIELD_MAP = {
      investor: {
        display: 'Investor',
        type: 'string',
        required: true
      },
      investorType: {
        display: 'Investor Type',
        type: 'string',
        required: false
      },
      date: {
        display: 'Date',
        type: 'date',
        required: false
      },
      preMoney: {
        display: 'Pre Money Val',
        type: 'money',
        required: false
      },
      raised: {
        display: 'Amount Raised',
        type: 'money',
        required: false
      },
      postMoney: {
        display: 'Post Money Val',
        type: 'money',
        required: false
      },
      // TODO: Make this a decimal money amount
      sharePrice: {
        display: 'Price Per Share',
        type: 'number',
        required: false
      },
      invested: {
        display: 'Invested',
        type: 'money',
        required: false
      },
      ownership: {
        display: 'Ownership',
        type: 'percentage',
        required: false
      },
      shares: {
        display: 'Shares',
        type: 'number',
        required: false
      }
    };

    this.state = {
      investments: []
    };

    this.getInvestmentList = this.getInvestmentList.bind(this);

    this.getInvestmentList();
  }

  getInvestmentList() {
    authFetch(`${this.props.API_URL_BASE}/investments`)
    .then(function(response) {
      if (response.ok) {
        return response.json();
      }
      else {
        return response.json().then(json => {
          throw new Error(json);
        });
      }
    })
    .then(json => {
      // Success
      json = preprocessJSON(json);
      console.log(json);
      this.setState({ investments: json });
    })
    .catch(err => {
      // Failure
      console.log(err);
      return err;
    });
  }

  render() {
    const investmentTables = this.state.investments.map(investment => {
      const API_URL = `${this.props.API_URL_BASE}/investments/` +
                      `${investment.id}/investors`;
      return (
        <div key={investment.id} className="ovc-edit-table-container">
          <h5>{investment.series}</h5>
          <EditTable API_URL={API_URL}
                     FIELDS={this.FIELDS}
                     FIELD_MAP={this.FIELD_MAP}
                     {...this.props} />
        </div>
      );
    });
    return (
      <div>{investmentTables}</div>
    );
  }
}

class MetricsSection extends React.Component {
  constructor(props) {
    super(props);

    this._NUM_QUARTERS = 9;
    this._QUARTERS_LIST = this.getQuarterList();

    this.FIELDS = ['metric'].concat(this._QUARTERS_LIST.map((quarter) =>
      quarter.format('YYYY[-]MM[-]DD'))
    );
    this.FIELD_MAP = {
      metric: {
        display: 'Metric',
        type: 'string',
        required: true
      }
    };
    this._QUARTERS_LIST.map((quarter) => {
      this.FIELD_MAP[quarter.format('YYYY[-]MM[-]DD')] = {
        display: quarter.format('[Q]Q YYYY'),
        type: 'money',
        required: false
      }
    });
  }

  getQuarterList() {
    return Array.from(Array(this._NUM_QUARTERS).keys()).map((i) =>
      moment().endOf('quarter').subtract(i, 'quarters')
    ).reverse();
  }

  render() {
    return (
      <div className="ovc-edit-table-container">
        <EditTable API_URL={`${this.props.API_URL_BASE}/metrics`}
                   FIELDS={this.FIELDS}
                   FIELD_MAP={this.FIELD_MAP}
                   {...this.props} />
      </div>
    );
  }
}

class CompanyPage extends React.Component {
  render() {
    return (
      <div className="ovc-founder-company-container">
        <h3>Team</h3>
        <TeamSection API_URL_BASE={this.props.API_URL_BASE}
                     USER_TYPE={this.props.USER_TYPE} />
        <h3>Board</h3>
        <BoardSection API_URL_BASE={this.props.API_URL_BASE}
                      USER_TYPE={this.props.USER_TYPE} />
        <h3>Investments</h3>
        <InvestmentSection API_URL_BASE={this.props.API_URL_BASE} />
        <h3>Investors</h3>
        <InvestorSection API_URL_BASE={this.props.API_URL_BASE} />
        <h3>KPIs</h3>
        <MetricsSection API_URL_BASE={this.props.API_URL_BASE} />
        <h3>Pitch Decks</h3>
        <h3>Customers</h3>
        <h3>Documents</h3>
      </div>
    );
  }
}

const companyWrapper = function(WrappedComponent, config) {
  return (props) => {
    const API_URL_BASE = config.apiUrlBase(props);
    return (<WrappedComponent API_URL_BASE={API_URL_BASE}
                              USER_TYPE={config.userType}
                              {...props} />);
  };
}

const founderConfig = {
  apiUrlBase: () => {
    return `${SERVER_URL}/api/v1/users/company`;
  },
  userType: 'founder',
};

const investorConfig = {
  apiUrlBase: (props) => {
    return `${SERVER_URL}/api/v1/users/portfolio/${props.match.params.companyId}`;
  },
  userType: 'investor',
}

const FounderCompanyPage = companyWrapper(CompanyPage, founderConfig);
const InvestorCompanyPage = companyWrapper(CompanyPage, investorConfig);

export {FounderCompanyPage, InvestorCompanyPage};

