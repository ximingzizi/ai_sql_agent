import Vue from 'vue'
import Router from 'vue-router'


Vue.use(Router)

export default new Router({
  mode: 'history',//去除描点
  routes: [
    {
      path: '/',// 斜杠地址
      name: 'Login',//组件名描述
      component: ()=> import('@/components/page/Login')
    },
    {
      path: '/chat',// 斜杠地址
      name: 'Chat',//组件名描述
      meta:{requireAuth:true}, //是否允许访问
      component: ()=> import('@/components/page/Chat')
    }
  ]
})
