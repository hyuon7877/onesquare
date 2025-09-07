/**
 * 댓글 시스템 컴포넌트
 * 중첩 댓글, 멘션, 실시간 업데이트 지원
 */
class CommentSystem {
    constructor(containerId, contentType, objectId) {
        this.container = document.getElementById(containerId);
        this.contentType = contentType;
        this.objectId = objectId;
        this.comments = [];
        this.replyTo = null;
        this.editingComment = null;
        this.mentionList = [];
        this.mentionDropdown = null;
        
        this.init();
    }
    
    init() {
        this.render();
        this.loadComments();
        this.attachEventListeners();
        this.initMentionSystem();
    }
    
    render() {
        const html = `
            <div class="comment-system">
                <!-- 댓글 작성 폼 -->
                <div class="comment-form-container">
                    <div class="comment-form">
                        <div class="comment-avatar">
                            <i class="bi bi-person-circle"></i>
                        </div>
                        <div class="comment-input-wrapper">
                            <div class="reply-indicator" style="display: none;">
                                <span class="reply-to"></span>
                                <button class="btn-cancel-reply">
                                    <i class="bi bi-x"></i>
                                </button>
                            </div>
                            <textarea 
                                class="form-control comment-input" 
                                placeholder="댓글을 작성하세요... @를 입력하여 사용자를 멘션할 수 있습니다."
                                rows="3"
                            ></textarea>
                            <div class="mention-dropdown" style="display: none;"></div>
                            <div class="comment-actions">
                                <div class="comment-tools">
                                    <button class="btn-tool" data-action="bold" title="굵게">
                                        <i class="bi bi-type-bold"></i>
                                    </button>
                                    <button class="btn-tool" data-action="italic" title="기울임">
                                        <i class="bi bi-type-italic"></i>
                                    </button>
                                    <button class="btn-tool" data-action="link" title="링크">
                                        <i class="bi bi-link-45deg"></i>
                                    </button>
                                    <button class="btn-tool" data-action="code" title="코드">
                                        <i class="bi bi-code"></i>
                                    </button>
                                </div>
                                <div class="comment-buttons">
                                    <button class="btn btn-secondary btn-cancel" style="display: none;">
                                        취소
                                    </button>
                                    <button class="btn btn-primary btn-submit-comment">
                                        <i class="bi bi-send"></i> 댓글 작성
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 댓글 목록 -->
                <div class="comments-container">
                    <div class="comments-header">
                        <h5 class="comments-title">
                            <i class="bi bi-chat-dots"></i> 
                            댓글 <span class="comment-count">0</span>
                        </h5>
                        <div class="comments-filter">
                            <select class="form-select form-select-sm">
                                <option value="newest">최신순</option>
                                <option value="oldest">오래된순</option>
                                <option value="popular">인기순</option>
                            </select>
                        </div>
                    </div>
                    <div class="comments-list">
                        <div class="loading-comments">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">댓글 로딩 중...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // 요소 참조
        this.commentInput = this.container.querySelector('.comment-input');
        this.commentsList = this.container.querySelector('.comments-list');
        this.commentCount = this.container.querySelector('.comment-count');
        this.replyIndicator = this.container.querySelector('.reply-indicator');
        this.replyToElement = this.container.querySelector('.reply-to');
        this.mentionDropdown = this.container.querySelector('.mention-dropdown');
    }
    
    attachEventListeners() {
        // 댓글 작성
        this.container.querySelector('.btn-submit-comment').addEventListener('click', () => {
            this.submitComment();
        });
        
        // 답글 취소
        this.container.querySelector('.btn-cancel-reply').addEventListener('click', () => {
            this.cancelReply();
        });
        
        // 취소 버튼
        this.container.querySelector('.btn-cancel').addEventListener('click', () => {
            this.cancelEdit();
        });
        
        // 텍스트 포맷팅 도구
        this.container.querySelectorAll('.btn-tool').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = btn.dataset.action;
                this.applyFormatting(action);
            });
        });
        
        // 정렬 변경
        this.container.querySelector('.comments-filter select').addEventListener('change', (e) => {
            this.sortComments(e.target.value);
        });
        
        // Ctrl+Enter로 댓글 작성
        this.commentInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.submitComment();
            }
        });
    }
    
    initMentionSystem() {
        this.commentInput.addEventListener('input', (e) => {
            this.handleMention(e.target.value);
        });
        
        // 멘션 드롭다운 외부 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideMentionDropdown();
            }
        });
    }
    
    async loadComments() {
        try {
            const response = await fetch(`/collaboration/comments/${this.contentType}/${this.objectId}/`);
            const data = await response.json();
            
            this.comments = data.comments;
            this.renderComments();
            this.updateCommentCount();
        } catch (error) {
            console.error('댓글 로드 실패:', error);
            this.showError('댓글을 불러올 수 없습니다.');
        }
    }
    
    renderComments() {
        if (this.comments.length === 0) {
            this.commentsList.innerHTML = `
                <div class="no-comments">
                    <i class="bi bi-chat-dots"></i>
                    <p>첫 번째 댓글을 작성해보세요!</p>
                </div>
            `;
            return;
        }
        
        const html = this.comments.map(comment => this.renderComment(comment)).join('');
        this.commentsList.innerHTML = html;
        
        // 댓글 액션 이벤트 리스너
        this.attachCommentActions();
    }
    
    renderComment(comment, isReply = false) {
        const isAuthor = comment.author.username === window.currentUser?.username;
        
        return `
            <div class="comment ${isReply ? 'comment-reply' : ''}" data-comment-id="${comment.id}">
                <div class="comment-avatar">
                    <i class="bi bi-person-circle"></i>
                </div>
                <div class="comment-content">
                    <div class="comment-header">
                        <div class="comment-author">
                            <strong>${comment.author.full_name}</strong>
                            <span class="username">@${comment.author.username}</span>
                        </div>
                        <div class="comment-meta">
                            <time class="comment-time" datetime="${comment.created_at}">
                                ${this.formatTime(comment.created_at)}
                            </time>
                            ${comment.is_edited ? '<span class="edited">(수정됨)</span>' : ''}
                        </div>
                    </div>
                    <div class="comment-body">
                        ${this.formatContent(comment.content)}
                        ${comment.mentioned_users.length > 0 ? `
                            <div class="mentioned-users">
                                ${comment.mentioned_users.map(user => 
                                    `<span class="mention-tag">@${user}</span>`
                                ).join(' ')}
                            </div>
                        ` : ''}
                    </div>
                    <div class="comment-footer">
                        <button class="btn-comment-action btn-reply" data-comment-id="${comment.id}">
                            <i class="bi bi-reply"></i> 답글
                        </button>
                        ${isAuthor ? `
                            <button class="btn-comment-action btn-edit" data-comment-id="${comment.id}">
                                <i class="bi bi-pencil"></i> 수정
                            </button>
                            <button class="btn-comment-action btn-delete" data-comment-id="${comment.id}">
                                <i class="bi bi-trash"></i> 삭제
                            </button>
                        ` : ''}
                    </div>
                    
                    <!-- 답글 -->
                    ${comment.replies && comment.replies.length > 0 ? `
                        <div class="replies">
                            ${comment.replies.map(reply => this.renderComment(reply, true)).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    attachCommentActions() {
        // 답글 버튼
        this.container.querySelectorAll('.btn-reply').forEach(btn => {
            btn.addEventListener('click', () => {
                const commentId = btn.dataset.commentId;
                const comment = this.findComment(commentId);
                this.setReplyTo(comment);
            });
        });
        
        // 수정 버튼
        this.container.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                const commentId = btn.dataset.commentId;
                const comment = this.findComment(commentId);
                this.startEdit(comment);
            });
        });
        
        // 삭제 버튼
        this.container.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', () => {
                const commentId = btn.dataset.commentId;
                this.deleteComment(commentId);
            });
        });
    }
    
    async submitComment() {
        const content = this.commentInput.value.trim();
        if (!content) return;
        
        const data = {
            content: content,
            parent_id: this.replyTo?.id || null
        };
        
        try {
            const response = await fetch(`/collaboration/comments/${this.contentType}/${this.objectId}/`, {
                method: this.editingComment ? 'PUT' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 댓글 추가 또는 업데이트
                if (this.editingComment) {
                    this.updateComment(result.comment);
                } else {
                    this.addComment(result.comment);
                }
                
                // 폼 리셋
                this.resetForm();
                
                // 성공 메시지
                showToast(this.editingComment ? '댓글이 수정되었습니다.' : '댓글이 작성되었습니다.');
            }
        } catch (error) {
            console.error('댓글 작성 실패:', error);
            showToast('댓글 작성에 실패했습니다.', 'error');
        }
    }
    
    addComment(comment) {
        if (comment.parent_id) {
            // 답글인 경우
            const parent = this.findComment(comment.parent_id);
            if (parent) {
                if (!parent.replies) parent.replies = [];
                parent.replies.push(comment);
            }
        } else {
            // 최상위 댓글
            this.comments.unshift(comment);
        }
        
        this.renderComments();
        this.updateCommentCount();
    }
    
    updateComment(updatedComment) {
        const comment = this.findComment(updatedComment.id);
        if (comment) {
            Object.assign(comment, updatedComment);
            this.renderComments();
        }
    }
    
    async deleteComment(commentId) {
        if (!confirm('댓글을 삭제하시겠습니까?')) return;
        
        try {
            const response = await fetch(`/collaboration/comments/${commentId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.removeComment(commentId);
                showToast('댓글이 삭제되었습니다.');
            }
        } catch (error) {
            console.error('댓글 삭제 실패:', error);
            showToast('댓글 삭제에 실패했습니다.', 'error');
        }
    }
    
    removeComment(commentId) {
        // 최상위 댓글에서 찾기
        const index = this.comments.findIndex(c => c.id == commentId);
        if (index !== -1) {
            this.comments.splice(index, 1);
        } else {
            // 답글에서 찾기
            this.comments.forEach(comment => {
                if (comment.replies) {
                    const replyIndex = comment.replies.findIndex(r => r.id == commentId);
                    if (replyIndex !== -1) {
                        comment.replies.splice(replyIndex, 1);
                    }
                }
            });
        }
        
        this.renderComments();
        this.updateCommentCount();
    }
    
    findComment(commentId) {
        // 최상위 댓글에서 찾기
        let found = this.comments.find(c => c.id == commentId);
        if (found) return found;
        
        // 답글에서 찾기
        for (const comment of this.comments) {
            if (comment.replies) {
                found = comment.replies.find(r => r.id == commentId);
                if (found) return found;
            }
        }
        
        return null;
    }
    
    setReplyTo(comment) {
        this.replyTo = comment;
        this.replyToElement.textContent = `@${comment.author.username}에게 답글`;
        this.replyIndicator.style.display = 'flex';
        this.commentInput.focus();
        
        // 버튼 텍스트 변경
        this.container.querySelector('.btn-submit-comment').innerHTML = 
            '<i class="bi bi-reply"></i> 답글 작성';
    }
    
    cancelReply() {
        this.replyTo = null;
        this.replyIndicator.style.display = 'none';
        this.container.querySelector('.btn-submit-comment').innerHTML = 
            '<i class="bi bi-send"></i> 댓글 작성';
    }
    
    startEdit(comment) {
        this.editingComment = comment;
        this.commentInput.value = comment.content;
        this.commentInput.focus();
        
        // UI 업데이트
        this.container.querySelector('.btn-submit-comment').innerHTML = 
            '<i class="bi bi-check"></i> 수정 완료';
        this.container.querySelector('.btn-cancel').style.display = 'inline-block';
    }
    
    cancelEdit() {
        this.editingComment = null;
        this.commentInput.value = '';
        
        // UI 리셋
        this.container.querySelector('.btn-submit-comment').innerHTML = 
            '<i class="bi bi-send"></i> 댓글 작성';
        this.container.querySelector('.btn-cancel').style.display = 'none';
    }
    
    resetForm() {
        this.commentInput.value = '';
        this.cancelReply();
        this.cancelEdit();
    }
    
    async handleMention(text) {
        const mentionMatch = text.match(/@(\w*)$/);
        
        if (mentionMatch) {
            const query = mentionMatch[1];
            
            if (query.length >= 1) {
                const users = await this.searchUsers(query);
                this.showMentionDropdown(users);
            } else {
                this.showMentionDropdown([]);
            }
        } else {
            this.hideMentionDropdown();
        }
    }
    
    async searchUsers(query) {
        try {
            const response = await fetch(`/collaboration/users/search/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            return data.users || [];
        } catch (error) {
            console.error('사용자 검색 실패:', error);
            return [];
        }
    }
    
    showMentionDropdown(users) {
        if (users.length === 0) {
            this.hideMentionDropdown();
            return;
        }
        
        const html = users.map(user => `
            <div class="mention-item" data-username="${user.username}">
                <i class="bi bi-person-circle"></i>
                <div class="mention-user">
                    <div class="mention-name">${user.full_name}</div>
                    <div class="mention-username">@${user.username}</div>
                </div>
            </div>
        `).join('');
        
        this.mentionDropdown.innerHTML = html;
        this.mentionDropdown.style.display = 'block';
        
        // 클릭 이벤트
        this.mentionDropdown.querySelectorAll('.mention-item').forEach(item => {
            item.addEventListener('click', () => {
                this.insertMention(item.dataset.username);
            });
        });
    }
    
    hideMentionDropdown() {
        this.mentionDropdown.style.display = 'none';
    }
    
    insertMention(username) {
        const text = this.commentInput.value;
        const mentionMatch = text.match(/@(\w*)$/);
        
        if (mentionMatch) {
            const newText = text.substring(0, mentionMatch.index) + `@${username} `;
            this.commentInput.value = newText;
            this.commentInput.focus();
        }
        
        this.hideMentionDropdown();
    }
    
    applyFormatting(action) {
        const textarea = this.commentInput;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);
        
        let formattedText = '';
        
        switch(action) {
            case 'bold':
                formattedText = `**${selectedText}**`;
                break;
            case 'italic':
                formattedText = `*${selectedText}*`;
                break;
            case 'link':
                const url = prompt('링크 URL을 입력하세요:');
                if (url) {
                    formattedText = `[${selectedText || '링크 텍스트'}](${url})`;
                }
                break;
            case 'code':
                formattedText = `\`${selectedText}\``;
                break;
        }
        
        if (formattedText) {
            textarea.value = textarea.value.substring(0, start) + formattedText + textarea.value.substring(end);
            textarea.focus();
            textarea.setSelectionRange(start, start + formattedText.length);
        }
    }
    
    formatContent(content) {
        // 마크다운 간단 파싱
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/@(\w+)/g, '<span class="mention">@$1</span>')
            .replace(/\n/g, '<br>');
    }
    
    formatTime(datetime) {
        const date = new Date(datetime);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) return '방금 전';
        if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}일 전`;
        
        return date.toLocaleDateString('ko-KR');
    }
    
    sortComments(sortBy) {
        switch(sortBy) {
            case 'newest':
                this.comments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                break;
            case 'oldest':
                this.comments.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                break;
            case 'popular':
                this.comments.sort((a, b) => (b.replies?.length || 0) - (a.replies?.length || 0));
                break;
        }
        
        this.renderComments();
    }
    
    updateCommentCount() {
        let count = this.comments.length;
        this.comments.forEach(comment => {
            if (comment.replies) {
                count += comment.replies.length;
            }
        });
        
        this.commentCount.textContent = count;
    }
    
    showError(message) {
        this.commentsList.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
}