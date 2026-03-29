const SESSION_TITLES_KEY = 'smartjournal_session_titles'

/**
 * 获取所有会话标题
 * @returns {Object} { sessionId: title, ... }
 */
export const getSessionTitles = () => {
  try {
    const stored = localStorage.getItem(SESSION_TITLES_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

/**
 * 保存会话标题
 * @param {string} sessionId
 * @param {string} title
 */
export const setSessionTitle = (sessionId, title) => {
  const titles = getSessionTitles()
  titles[sessionId] = title
  localStorage.setItem(SESSION_TITLES_KEY, JSON.stringify(titles))
}

/**
 * 删除会话标题
 * @param {string} sessionId
 */
export const removeSessionTitle = (sessionId) => {
  const titles = getSessionTitles()
  delete titles[sessionId]
  localStorage.setItem(SESSION_TITLES_KEY, JSON.stringify(titles))
}

/**
 * 获取单个会话标题
 * @param {string} sessionId
 * @param {string} fallback 默认标题
 * @returns {string}
 */
export const getSessionTitle = (sessionId, fallback = '新会话') => {
  return getSessionTitles()[sessionId] || fallback
}
