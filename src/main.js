// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import router from './router'
import axios from 'axios'
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
/* 设置cookie,session跨域配置 */
axios.defaults.withCredentials=true;
/* 设置post请求体,请求格式为json*/
axios.defaults.headers.post['Content-Type'] = 'application/json'
/* 设置全局axios写法 */
Vue.prototype.$http = axios

Vue.use(ElementUI);
Vue.config.productionTip = false





/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})
