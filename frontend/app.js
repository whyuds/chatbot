document.addEventListener('DOMContentLoaded', () => {
    // 确保 highlight.js 已正确初始化
    if (typeof hljs === 'undefined') {
        console.error('highlight.js 未加载，代码高亮功能将不可用');
        // 创建一个空的 hljs 对象，防止代码报错
        window.hljs = {
            highlight: () => ({ value: '' }),
            highlightAuto: () => ({ value: '' }),
            highlightElement: () => {},
            getLanguage: () => null
        };
    }

    const API_BASE = 'http://localhost:8000';
    
    // DOM elements
    const newChatBtn = document.getElementById('newChat');
    const conversationList = document.getElementById('conversationList');
    const messageContainer = document.getElementById('messageContainer');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendButton');
    
    let currentConversationId = null;

    // Fetch conversations
    async function fetchConversations() {
        try {
            const res = await fetch(`${API_BASE}/conversations`);
            const conversations = await res.json();
            renderConversations(conversations);
        } catch (err) {
            console.error('Failed to fetch conversations:', err);
        }
    }

    // Render conversations list
    function renderConversations(conversations) {
        conversationList.innerHTML = conversations.map(conv => 
            `<div class="conversation-item ${conv.id === currentConversationId ? 'active' : ''}" data-id="${conv.id}">
                <div class="conv-title">${conv.title}</div>
                <div class="conv-date">${new Date(conv.updated_at).toLocaleString()}</div>
                <div class="delete-btn">×</div>
            </div>`
        ).join('');
    }

    // Create new conversation
    async function createConversation() {
        try {
            const res = await fetch(`${API_BASE}/conversations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: 'New Chat' })
            });
            const newConv = await res.json();
            currentConversationId = newConv.id;
            await fetchConversations();
            messageContainer.innerHTML = '';
        } catch (err) {
            console.error('Failed to create conversation:', err);
        }
    }

    // 配置marked选项
    marked.setOptions({
        highlight: function(code, lang) {
            try {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            } catch (e) {
                console.error('代码高亮出错:', e);
                return code; // 出错时返回原始代码
            }
        },
        breaks: true,
        gfm: true
    });

    // Load conversation
    async function loadConversation(conversationId) {
        try {
            const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
            const messages = await res.json();
            messageContainer.innerHTML = '';
            messages.forEach(msg => addMessage(msg.role, msg.content));
        } catch (err) {
            console.error('Failed to load conversation:', err);
        }
    }

    function handleDeleteConversation(convId, event) {
        event.stopPropagation();
        fetch(`${API_BASE}/conversations/${convId}`, { method: 'DELETE' })
            .then(() => {
                if(currentConversationId === convId) {
                    messageContainer.innerHTML = '';
                    currentConversationId = null;
                }
                fetchConversations();
            });
    }

    // Add delete handler via event delegation
    conversationList.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const convId = parseInt(e.target.closest('.conversation-item').dataset.id);
            handleDeleteConversation(convId, e);
        }
    });

    // Event listeners
    newChatBtn.addEventListener('click', createConversation);
    
    // 修复重复的事件监听器
    conversationList.addEventListener('click', (e) => {
        if (e.target.classList.contains('conversation-item') || e.target.closest('.conversation-item')) {
            const convItem = e.target.closest('.conversation-item');
            const deleteBtn = convItem.querySelector('.delete-btn');
            
            if (!deleteBtn.contains(e.target)) {
                const convId = parseInt(convItem.dataset.id);
                currentConversationId = convId;
                
                // 更新高亮状态
                document.querySelectorAll('.conversation-item').forEach(item => {
                    item.classList.remove('active');
                });
                convItem.classList.add('active');
                
                loadConversation(convId);
            }
        }
    });

    // Add send button handler
    sendBtn.addEventListener('click', sendMessage);
    
    // Handle Enter key in textarea
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 修改addMessage函数以支持Markdown，添加错误处理
    function addMessage(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        if (role === 'assistant') {
            // 对助手消息使用Markdown解析
            const markdownDiv = document.createElement('div');
            markdownDiv.className = 'markdown-content';
            markdownDiv.innerHTML = marked.parse(content);
            msgDiv.appendChild(markdownDiv);
            
            // 对代码块应用语法高亮，添加错误处理
            try {
                msgDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            } catch (e) {
                console.error('代码高亮应用失败:', e);
            }
        } else {
            // 用户消息保持纯文本
            msgDiv.textContent = content;
        }
        
        messageContainer.appendChild(msgDiv);
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }

    // 修改发送消息函数，使用流式API
    async function sendMessage() {
        const content = messageInput.value.trim();
        if (!content || !currentConversationId) return;
    
        // 添加用户消息
        addMessage('user', content);
        messageInput.value = '';
    
        try {
            // 创建助手消息占位符
            const assistantMsgElement = document.createElement('div');
            assistantMsgElement.className = 'message assistant';
            
            // 创建Markdown内容容器
            const markdownDiv = document.createElement('div');
            markdownDiv.className = 'markdown-content';
            assistantMsgElement.appendChild(markdownDiv);
            
            messageContainer.appendChild(assistantMsgElement);
            messageContainer.scrollTop = messageContainer.scrollHeight;
    
            // 使用流式API
            const response = await fetch(`${API_BASE}/conversations/${currentConversationId}/messages/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
    
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
    
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullResponse = '';
    
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
    
                // 解码并处理每个数据块
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const { chunk: textChunk, done: isDone } = JSON.parse(line);
                            if (textChunk) {
                                fullResponse += textChunk;
                                // 实时更新Markdown渲染
                                markdownDiv.innerHTML = marked.parse(fullResponse);
                                
                                // 对新的代码块应用语法高亮，添加错误处理
                                try {
                                    assistantMsgElement.querySelectorAll('pre code').forEach((block) => {
                                        hljs.highlightElement(block);
                                    });
                                } catch (e) {
                                    console.error('流式响应中代码高亮应用失败:', e);
                                }
                                
                                messageContainer.scrollTop = messageContainer.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Error parsing JSON:', e);
                        }
                    }
                }
            }
            
            // 流式响应完成后，刷新对话列表以获取可能更新的标题
            await fetchConversations();
        } catch (err) {
            console.error('Failed to send message:', err);
            addMessage('error', '消息发送失败');
        }
    }

    // 修改loadConversation函数以支持Markdown
    async function loadConversation(conversationId) {
        try {
            const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
            const messages = await res.json();
            messageContainer.innerHTML = '';
            messages.forEach(msg => addMessage(msg.role, msg.content));
        } catch (err) {
            console.error('Failed to load conversation:', err);
        }
    }

    // 修改初始化逻辑：获取对话列表并加载第一个
    async function initializeApp() {
        try {
            const response = await fetch(`${API_BASE}/conversations`);
            const conversations = await response.json();
            
            if (conversations.length > 0) {
                const latestConversation = conversations[0];
                currentConversationId = latestConversation.id;
                await loadConversation(latestConversation.id);
                
                // 确保在渲染后添加高亮
                setTimeout(() => {
                    const activeItem = document.querySelector(`[data-id="${latestConversation.id}"]`);
                    if (activeItem) {
                        activeItem.classList.add('active');
                    }
                }, 100);
            } else {
                createConversation();
            }
        }
        catch (error) {
            console.error('Failed to fetch conversations:', error);   
        }
    }

    // 初始化应用
    fetchConversations();
    initializeApp();
});