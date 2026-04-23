<script>
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import * as echarts from 'echarts'

export default {
  name: "Chat",
  data() {
    return {
      thinking: false,
      userId: "",
      inputMessage: "2023年9月份订单销售情况，请用柱状图表给我分析一下",
      fileInfo: null,
      userAvatar: require('@/assets/image/user.jpeg'),
      botAvatar: require('@/assets/image/bot.jpeg'),
      activeChatId: "",
      chatList: [],
      currentEventSource: null,
      suggestionPrompts: [
        "2023年9月份订单销售情况，请用柱状图表给我分析一下",
        "给我生成一个销售趋势仪表盘",
        "帮我分析订单数据并给出结论",
        "我上传了文件，帮我检查缺失值和重复数据",
      ],
      supervisorStageTexts: [
        "主智能体正在理解你的问题...",
        "主智能体正在挑选合适的子智能体...",
        "子智能体正在处理任务...",
        "主智能体正在汇总多个子智能体结果...",
        "主智能体正在整理最终答复..."
      ],
    }
  },
  computed: {
    currentChat() {
      return this.chatList.find((chat) => chat.id === this.activeChatId) || null
    },
    currentMessages() {
      return this.currentChat ? this.currentChat.messages : []
    }
  },
  mounted() {
    this.userId = localStorage.getItem("user_id") || "";
  },
  beforeDestroy() {
    this.closeEventSource();
  },
  methods: {
    getAgentDisplayName(agentName) {
      const agentNameMap = {
        sql_specialist: "SQL 子智能体",
        chart_specialist: "图表子智能体",
        analyze_specialist: "分析子智能体",
        dashboard_specialist: "仪表盘子智能体",
        file_specialist: "文件子智能体",
      };
      return agentNameMap[agentName] || agentName;
    },
    formatAgentCalls(agentCalls) {
      const calls = Array.isArray(agentCalls) ? agentCalls : [];
      if (!calls.length) {
        return "无";
      }
      return calls.map((agentName) => this.getAgentDisplayName(agentName)).join("、");
    },
    getSupervisorStageText(stepIndex) {
      const stages = this.supervisorStageTexts;
      if (!stages.length) {
        return "主智能体正在处理中...";
      }
      return stages[Math.min(stepIndex, stages.length - 1)];
    },
    normalizeChartOption(rawOption) {
      let option = rawOption;

      if (!option) {
        return null;
      }

      if (typeof option === "string") {
        try {
          option = JSON.parse(option);
        } catch (error) {
          return null;
        }
      }

      if (!option || typeof option !== "object" || Array.isArray(option)) {
        return null;
      }

      return option;
    },
    createMessageId() {
      return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    },
    getChatPreview(chat) {
      const lastMessage = Array.isArray(chat.messages) ? chat.messages[chat.messages.length - 1] : null;
      if (!lastMessage || !lastMessage.content) {
        return "等待新的问题";
      }
      return String(lastMessage.content).replace(/\s+/g, " ").slice(0, 36);
    },
    useSuggestion(prompt) {
      this.inputMessage = prompt;
    },
    selectChat(id) {
      this.activeChatId = id;
    },
    newChat() {
      const id = this.createMessageId();
      this.chatList.push({
        id,
        title: "新对话",
        messages: [],
      });
      this.activeChatId = id;
    },
    ensureActiveChat() {
      if (this.currentChat) {
        return this.currentChat;
      }

      const id = this.createMessageId();
      const chat = {
        id,
        title: this.inputMessage || "新对话",
        messages: [],
      };
      this.chatList.push(chat);
      this.activeChatId = id;
      return chat;
    },
    closeEventSource() {
      if (this.currentEventSource) {
        this.currentEventSource.close();
        this.currentEventSource = null;
      }
    },
    uploadFile(response) {
      const formData = new FormData();
      formData.append("user_id", this.userId);
      formData.append("file", response.file);

      this.$http.post("http://localhost:8000/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      }).then((res) => {
        if (res.data.code === 200) {
          this.fileInfo = res.data.data;
          this.$message.success("上传成功");
          return;
        }
        this.$message.error(res.data.msg || "上传失败");
      }).catch(() => {
        this.$message.error("上传失败");
      });
    },
    formatMessage(content) {
      return DOMPurify.sanitize(marked.parse(content || ""));
    },
    renderChartMessage(message) {
      const payload = message.payload || {};
      const chartJson = payload.chartJson;
      if (!chartJson) {
        message.content = message.content || "后端没有返回图表配置。";
        return;
      }

      this.$nextTick(() => {
        const dom = document.getElementById(`chart-${message.id}`);
        if (!dom) {
          return;
        }

        try {
          const option = this.normalizeChartOption(chartJson);
          if (!option) {
            // 当前后端偶尔会把标题或说明文字塞进 chartJson，这里先降级为文本提示，避免 ECharts 直接报错。
            message.content = `${message.content ? `${message.content}\n\n` : ""}图表配置格式无效，无法渲染图表。原始数据：${String(chartJson)}`;
            return;
          }
          const chart = echarts.getInstanceByDom(dom) || echarts.init(dom);
          chart.clear();
          chart.setOption(option);
        } catch (error) {
          console.error("图表渲染失败:", error);
          message.content = `${message.content ? `${message.content}\n\n` : ""}图表渲染失败。`;
        }
      });
    },
    applyFinalMessage(message, data) {
      const type = data.type || "text";
      const payload = data.payload || {};

      message.isStreaming = false;
      message.statusText = "";
      message.type = type;
      message.payload = payload;
      message.meta = data.meta || message.meta || null;

      if (type === "text") {
        message.content = payload.content || message.content || "";
        return;
      }

      if (type === "chart") {
        message.content = payload.msg || "";
        this.renderChartMessage(message);
        return;
      }

      if (type === "analyze") {
        message.content = payload.result || "";
        this.renderChartMessage(message);
        return;
      }

      if (type === "dashboard") {
        message.content = payload.message || "";
        return;
      }

      if (type === "file") {
        message.content = payload.summary || "";
        return;
      }

      message.type = "text";
      message.content = payload.content || message.content || "";
    },
    updateStreamingAssistant(message, chunkText) {
      const nextStep = (message.streamStep || 0) + 1;
      message.streamStep = nextStep;
      message.streamBuffer = `${message.streamBuffer || ""}${chunkText || ""}`;
      message.statusText = this.getSupervisorStageText(nextStep - 1);

      // supervisor 的流式内容本身是最终 JSON 的片段，前端不直接展示，避免用户看到半截 JSON。
      // 这里保留原始流式内容到 streamBuffer，等 final 到达时再渲染真正结果。
      if (!message.content) {
        message.content = message.statusText;
      }
    },
    updateObservabilityMeta(message, meta) {
      if (!meta) {
        return;
      }
      message.meta = meta;
    },
    sendMessage() {
      const question = this.inputMessage.trim();
      if (!question) {
        return;
      }

      const chat = this.ensureActiveChat();
      if (!chat.title || chat.title === "新对话") {
        chat.title = question;
      }

      const userMessage = {
        id: this.createMessageId(),
        role: "user",
        type: "text",
        payload: null,
        content: question,
      };
      const assistantMessage = {
        id: this.createMessageId(),
        role: "assistant",
        type: "text",
        payload: null,
        content: "主智能体正在处理中...",
        isStreaming: true,
        statusText: "主智能体正在处理中...",
        streamBuffer: "",
        streamStep: 0,
        meta: null,
      };

      chat.messages.push(userMessage);
      chat.messages.push(assistantMessage);
      this.inputMessage = "";
      this.thinking = true;

      this.closeEventSource();
      const params = new URLSearchParams({
        question,
        user_id: this.userId,
      });
      if (this.fileInfo && this.fileInfo.file_path) {
        params.append("file_path", this.fileInfo.file_path);
      }

      const sse = new EventSource(`http://localhost:8000/chat/stream?${params.toString()}`);
      this.currentEventSource = sse;

      sse.onmessage = (event) => {
        const data = JSON.parse(event.data || "{}");
        console.log("接收数据：", data);

        if (data.event === "chunk") {
          this.thinking = false;
          this.updateStreamingAssistant(assistantMessage, data.content || "");
          this.updateObservabilityMeta(assistantMessage, data.meta || null);
          return;
        }

        if (data.event === "final") {
          this.thinking = false;
          this.applyFinalMessage(assistantMessage, data);
          this.closeEventSource();
          return;
        }

        if (data.event === "error" || data.error) {
          this.thinking = false;
          assistantMessage.isStreaming = false;
          assistantMessage.statusText = "";
          assistantMessage.type = "text";
          assistantMessage.content = data.content || "聊天出错";
          this.updateObservabilityMeta(assistantMessage, data.meta || null);
          this.closeEventSource();
        }
      };

      sse.onerror = () => {
        this.thinking = false;
        assistantMessage.isStreaming = false;
        assistantMessage.statusText = "";
        if (!assistantMessage.content) {
          assistantMessage.type = "text";
          assistantMessage.content = "连接已中断，请重试";
        }
        this.closeEventSource();
      };
    },
  }
}
</script>

<template>
  <el-container class="chat-shell">
    <el-aside width="320px" class="chat-sidebar">
      <div class="sidebar-brand">
        <div class="brand-mark">A</div>
        <div>
          <div class="brand-title">Agent Analytics</div>
          <div class="brand-subtitle">多智能体数据分析工作台</div>
        </div>
      </div>

      <div class="sidebar-card sidebar-intro">
        <div class="sidebar-kicker">Workspace</div>
        <h2>把数据库问答、图表、分析和文件处理放进一个对话入口。</h2>
        <p>当前前端已经对齐 supervisor 流式协议，结果按类型统一渲染。</p>
        <el-button type="primary" icon="el-icon-plus" class="sidebar-create" @click="newChat">新建对话</el-button>
      </div>

      <div class="sidebar-card session-card">
        <div class="section-title">会话列表</div>
        <div v-if="!chatList.length" class="empty-session">
          暂无会话，先发送一个问题。
        </div>
        <div
          v-for="chat in chatList"
          :key="chat.id"
          class="session-item"
          :class="{ active: activeChatId === chat.id }"
          @click="selectChat(chat.id)"
        >
          <div class="session-item-title">{{ chat.title || '新对话' }}</div>
          <div class="session-item-preview">{{ getChatPreview(chat) }}</div>
        </div>
      </div>
    </el-aside>

    <el-container class="chat-stage">
      <el-header class="chat-topbar">
        <div class="topbar-copy">
          <div class="topbar-label">Supervisor Streaming UI</div>
          <h1>AI 智能数据分析助手</h1>
          <p>统一聊天协议，主智能体流式返回，子智能体按任务编排执行。</p>
        </div>

        <div class="topbar-actions">
          <div class="status-chip">
            <span class="status-dot"></span>
            后端已连接
          </div>
          <div class="user-chip">用户 {{ userId || '未登录' }}</div>
          <el-button plain>退出登录</el-button>
        </div>
      </el-header>

      <el-main class="chat-workspace">
        <div class="workspace-glow"></div>

        <div v-if="!currentMessages.length" class="empty-hero">
          <div class="empty-kicker">Start Here</div>
          <h2>一个入口，把问答、图表、分析和仪表盘全部打通。</h2>
          <p>直接输入问题，主智能体会选择合适的子智能体并用统一结果协议返回。</p>
          <div class="suggestion-list">
            <button
              v-for="prompt in suggestionPrompts"
              :key="prompt"
              type="button"
              class="suggestion-chip"
              @click="useSuggestion(prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </div>

        <div v-if="currentMessages.length" class="message-stream">
          <div
            v-for="x in currentMessages"
            :key="x.id"
            class="chat-message"
            :class="x.role"
          >
            <div class="avatar-wrap">
              <el-avatar :src="x.role === 'user' ? userAvatar : botAvatar"></el-avatar>
            </div>

            <div class="message-body">
              <div class="message-meta">
                <span class="message-role">{{ x.role === 'user' ? '你' : 'Supervisor' }}</span>
                <span class="message-type">{{ x.type || 'text' }}</span>
              </div>

              <div v-if="x.type === 'text'">
                <div v-html="formatMessage(x.content)" class="bubble"></div>
                <div v-if="x.isStreaming" class="agent-status">
                  <div class="agent-status-label">多智能体编排中</div>
                  <div class="agent-status-text">{{ x.statusText || '主智能体正在处理中...' }}</div>
                </div>
              </div>

              <div v-else-if="x.type === 'chart'">
                <div v-if="x.content" v-html="formatMessage(x.content)" class="bubble"></div>
                <div :id="`chart-${x.id}`" class="chart-box"></div>
              </div>

              <div v-else-if="x.type === 'analyze'">
                <div v-if="x.payload && x.payload.table" class="rich-block data-table-wrap">
                  <el-table :data="(x.payload.table && x.payload.table.data) || []" style="width: 100%;">
                    <el-table-column
                      v-for="column in ((x.payload.table && x.payload.table.column_name) || [])"
                      :key="`${x.id}_${column}`"
                      :prop="column"
                      :label="column"
                    ></el-table-column>
                  </el-table>
                </div>
                <div v-if="x.content" v-html="formatMessage(x.content)" class="bubble"></div>
                <div v-if="x.payload && x.payload.chartJson" :id="`chart-${x.id}`" class="chart-box"></div>
              </div>

              <div v-else-if="x.type === 'dashboard'">
                <div v-if="x.content" v-html="formatMessage(x.content)" class="bubble"></div>
                <a
                  v-if="x.payload && x.payload.url"
                  :href="x.payload.url"
                  target="_blank"
                  class="message-link"
                >
                  打开仪表盘
                </a>
              </div>

              <div v-else-if="x.type === 'file'">
                <div v-if="x.content" v-html="formatMessage(x.content)" class="bubble"></div>
                <a
                  v-if="x.payload && x.payload.downloadUrl"
                  :href="x.payload.downloadUrl"
                  target="_blank"
                  class="message-link"
                >
                  下载处理后的文件
                </a>
              </div>

              <div v-if="x.role === 'assistant' && x.meta" class="observability-panel">
                <div class="observability-title">本次调用观测</div>
                <div class="observability-row">
                  <span class="observability-key">调用子智能体</span>
                  <span class="observability-value">
                    {{ formatAgentCalls(x.meta.agentCalls) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="thinking" class="chat-message assistant">
            <div class="avatar-wrap">
              <el-avatar :src="botAvatar"></el-avatar>
            </div>
            <div class="message-body">
              <div class="message-meta">
                <span class="message-role">Supervisor</span>
                <span class="message-type">thinking</span>
              </div>
              <div class="bubble typing-indicator">正在思考...</div>
            </div>
          </div>
        </div>
      </el-main>

      <el-footer class="chat-composer">
        <div class="composer-panel">
          <div class="composer-header">
            <div>
              <div class="section-title">输入问题</div>
              <div class="composer-help">支持普通问答、图表、分析、仪表盘和文件分析。</div>
            </div>
            <div v-if="fileInfo" class="file-pill">
              已挂载文件：{{ fileInfo.file_name }}
            </div>
          </div>

          <el-form>
            <el-form-item class="composer-input">
              <el-input
                type="textarea"
                v-model="inputMessage"
                :autosize="{ minRows: 3, maxRows: 6 }"
                placeholder="输入你的问题，主智能体会自动选择合适的子智能体..."
              ></el-input>
            </el-form-item>

            <div class="composer-actions">
              <el-upload
                action="http://localhost:8000/upload"
                :http-request="uploadFile"
                :show-file-list="true"
              >
                <el-button icon="el-icon-upload2">上传文件</el-button>
              </el-upload>

              <el-button type="success" icon="el-icon-message" @click="sendMessage">发送消息</el-button>
            </div>
          </el-form>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<style scoped>
.chat-shell * {
  box-sizing: border-box;
}

.chat-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(251, 146, 60, 0.24), transparent 28%),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 24%),
    linear-gradient(135deg, #07111f 0%, #0f172a 45%, #172033 100%);
  color: #e2e8f0;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.chat-sidebar {
  padding: 28px 22px;
  border-right: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(3, 10, 24, 0.72);
  backdrop-filter: blur(18px);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f97316, #fb7185);
  color: #fff;
  font-size: 22px;
  font-weight: 800;
  box-shadow: 0 18px 30px rgba(249, 115, 22, 0.25);
}

.brand-title {
  color: #f8fafc;
  font-size: 20px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 13px;
}

.sidebar-card {
  margin-bottom: 18px;
  padding: 20px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.68);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.sidebar-kicker,
.topbar-label,
.empty-kicker {
  color: #f59e0b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-intro h2,
.empty-hero h2 {
  margin: 12px 0 10px;
  color: #f8fafc;
  line-height: 1.25;
}

.sidebar-intro p,
.topbar-copy p,
.empty-hero p,
.composer-help,
.session-item-preview,
.empty-session {
  color: #94a3b8;
  line-height: 1.6;
}

.sidebar-create {
  width: 100%;
  margin-top: 18px;
}

.section-title {
  color: #f8fafc;
  font-size: 15px;
  font-weight: 700;
}

.session-item {
  margin-top: 12px;
  padding: 14px 16px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: rgba(30, 41, 59, 0.52);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.session-item:hover {
  transform: translateY(-1px);
  border-color: rgba(251, 146, 60, 0.35);
  background: rgba(30, 41, 59, 0.78);
}

.session-item.active {
  border-color: rgba(251, 146, 60, 0.45);
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.18), rgba(15, 23, 42, 0.9));
}

.session-item-title {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 700;
}

.chat-stage {
  min-width: 0;
}

.chat-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 34px 18px;
  background: transparent;
  color: #e2e8f0;
  height: auto !important;
}

.topbar-copy h1 {
  margin: 10px 0 8px;
  color: #ffffff;
  font-size: 34px;
  line-height: 1.1;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-chip,
.user-chip,
.file-pill,
.message-type {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #cbd5e1;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.12);
}

.chat-workspace {
  position: relative;
  overflow: auto;
  padding: 10px 34px 24px;
  background: transparent;
}

.workspace-glow {
  position: absolute;
  top: 0;
  left: 50%;
  width: 460px;
  height: 460px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(249, 115, 22, 0.13), transparent 68%);
  transform: translateX(-50%);
  pointer-events: none;
  filter: blur(8px);
}

.empty-hero,
.message-stream,
.composer-panel {
  position: relative;
  z-index: 1;
}

.empty-hero {
  max-width: 920px;
  margin: 28px auto 0;
  padding: 42px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 32px;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.62)),
    url(../../assets/image/login.jpeg) center/cover no-repeat;
  box-shadow: 0 30px 80px rgba(2, 6, 23, 0.34);
}

.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.suggestion-chip {
  padding: 12px 16px;
  border: 1px solid rgba(251, 146, 60, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: #f8fafc;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.suggestion-chip:hover {
  background: rgba(249, 115, 22, 0.12);
  border-color: rgba(251, 146, 60, 0.4);
  transform: translateY(-1px);
}

.message-stream {
  max-width: 1120px;
  margin: 0 auto;
  padding-right: 4px;
}

.chat-message {
  display: flex;
  gap: 14px;
  margin: 18px 0;
  align-items: flex-start;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.avatar-wrap {
  flex-shrink: 0;
}

.message-body {
  max-width: min(860px, calc(100% - 72px));
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.message-role {
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
}

.message-type {
  padding: 5px 10px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.bubble {
  padding: 16px 18px;
  border-radius: 22px;
  line-height: 1.7;
  backdrop-filter: blur(12px);
  box-shadow: 0 16px 38px rgba(2, 6, 23, 0.22);
}

.user .bubble {
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-right-radius: 8px;
}

.assistant .bubble {
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-top-left-radius: 8px;
}

.chart-box {
  width: 100%;
  min-height: 340px;
  margin-top: 12px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 26px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.18);
}

.rich-block {
  margin-bottom: 12px;
}

.data-table-wrap {
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.message-link {
  display: inline-block;
  margin-top: 12px;
  padding: 12px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #f59e0b;
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.message-link:hover {
  background: rgba(249, 115, 22, 0.12);
  color: #fb923c;
}

.typing-indicator {
  min-width: 120px;
}

.agent-status {
  margin-top: 10px;
  padding: 14px 16px;
  border: 1px dashed rgba(14, 165, 233, 0.34);
  border-radius: 18px;
  background: rgba(14, 165, 233, 0.06);
}

.agent-status-label {
  color: #38bdf8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.agent-status-text {
  margin-top: 6px;
  color: #cbd5e1;
  font-size: 14px;
}

.observability-panel {
  margin-top: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.72);
}

.observability-title {
  margin-bottom: 8px;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
}

.observability-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0;
  color: #cbd5e1;
  font-size: 13px;
}

.observability-key {
  color: #94a3b8;
}

.observability-value {
  text-align: right;
  color: #f8fafc;
  font-weight: 600;
  word-break: break-all;
}

.chat-composer {
  padding: 10px 34px 30px;
  background: transparent;
  height: auto !important;
}

.composer-panel {
  max-width: 1120px;
  margin: 0 auto;
  padding: 22px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 28px;
  background: rgba(7, 15, 28, 0.82);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.3);
}

.composer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.composer-input {
  margin-bottom: 14px;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.chat-composer /deep/ .el-textarea__inner {
  min-height: 96px !important;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.86);
  color: #f8fafc;
}

.chat-composer /deep/ .el-textarea__inner:focus {
  border-color: rgba(249, 115, 22, 0.65);
}

.chat-composer /deep/ .el-upload-list__item-name,
.chat-composer /deep/ .el-upload-list__item-status-label,
.chat-composer /deep/ .el-upload-list__item .el-icon-close {
  color: #e2e8f0;
}

.message-stream /deep/ .el-table,
.message-stream /deep/ .el-table tr,
.message-stream /deep/ .el-table th,
.message-stream /deep/ .el-table td {
  background: #ffffff;
}

@media (max-width: 1200px) {
  .chat-shell {
    display: block;
  }

  .chat-sidebar {
    width: auto !important;
    border-right: 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }
}

@media (max-width: 768px) {
  .chat-topbar,
  .chat-workspace,
  .chat-composer,
  .chat-sidebar {
    padding-left: 18px;
    padding-right: 18px;
  }

  .chat-topbar,
  .composer-header,
  .composer-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .empty-hero,
  .composer-panel,
  .sidebar-card {
    padding: 18px;
    border-radius: 22px;
  }

  .message-body {
    max-width: calc(100% - 60px);
  }
}
</style>
