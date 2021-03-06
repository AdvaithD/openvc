/*
 * TODO: This is not secure and is vulnerable to XSS. Move to HttpOnly cookies.
 *       This requires a server-side implementation.
 */

// TODO: Consider moving to this: https://github.com/js-cookie/js-cookie/
const getCookie = function(name) {
  let cookieValue;
  if (document.cookie && document.cookie !== '') {
    let cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

const storeToken = function(token) {
  localStorage.setItem('apiToken', token);
};

const getToken = function() {
  return localStorage.getItem('apiToken');
};

const getCSRFToken = function() {
  return getCookie('csrftoken');
};

export {storeToken, getToken};
