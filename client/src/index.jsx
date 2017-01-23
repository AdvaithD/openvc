import React from 'react';
import ReactDOM from 'react-dom';
import {Router, Route, IndexRoute, Link, hashHistory} from 'react-router';

import Bootstrap from 'bootstrap/dist/css/bootstrap.css';

import './index.scss';

import {WebsiteHeader, WebsiteHome, WebsiteAbout, WebsiteLogin, WebsiteFooter,
        WebsiteApp} from './website/website.jsx';
import {LoginForm, SignupForm, StartupForm,
        ContactForm} from './website/login.jsx';

import FounderApp from './founder/home.jsx';

class AppContainer extends React.Component {
  render() {
    const {main, topnav} = this.props;

    return (
      <div className="ovc-app-container">
        <div className="ovc-topnav-container">{topnav}</div>
        <div className="ovc-main-container">{main}</div>
      </div>
    );
  }
}

class App extends React.Component {
  render() {
    return (
      <Router history={hashHistory}>
        <Route path="/" component={AppContainer}>
          <IndexRoute components={{main: WebsiteHome,
                                   topnav: WebsiteHeader}} />
          <Route path="home" components={{main: WebsiteHome,
                                          topnav: WebsiteHeader}} />
          <Route path="about" components={{main: WebsiteAbout,
                                           topnav: WebsiteHeader}} />
          <Route path="login" components={{main: WebsiteLogin,
                                           topnav: WebsiteHeader}}>
            <IndexRoute component={LoginForm} />
            <Route path="signup" components={SignupForm} />
            <Route path="startup" components={StartupForm} />
            <Route path="contact" components={ContactForm} />
          </Route>

          <Route path="founder" components={{main: FounderApp}} />
        </Route>
      </Router>
    );
  }
}

ReactDOM.render(
  <App />,
  document.getElementById('app')
);

