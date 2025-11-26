# 🔑 프론트엔드 토큰 자동 갱신 가이드

Access Token 만료 시 자동으로 Refresh Token을 사용해 갱신하는 프론트엔드 구현 가이드입니다.

---

## 📋 목차

1. [Axios Interceptor 구현](#axios-interceptor-구현)
2. [Fetch API 구현](#fetch-api-구현)
3. [React 구현 예시](#react-구현-예시)
4. [Vue.js 구현 예시](#vuejs-구현-예시)

---

## 🚀 Axios Interceptor 구현

### 설치

```bash
npm install axios
```

### 구현 코드

```javascript
// src/api/axios.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 토큰 저장소
let accessToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');
let isRefreshing = false;
let failedQueue = [];

// 대기 중인 요청 처리
const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// 요청 인터셉터: Access Token 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 401 에러 시 자동 갱신
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // 401 에러이고, 재시도하지 않은 요청인 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 이미 갱신 중이면 대기열에 추가
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      // Refresh Token이 없으면 로그인 페이지로
      if (!refreshToken) {
        console.error('Refresh Token이 없습니다. 로그인이 필요합니다.');
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Refresh Token으로 새 Access Token 요청
        const response = await axios.post(`${API_BASE_URL}/api/web/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: new_refresh_token } = response.data;

        // 새 토큰 저장
        accessToken = access_token;
        refreshToken = new_refresh_token;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', new_refresh_token);

        // 대기 중인 요청들 처리
        processQueue(null, access_token);

        // 원래 요청 재시도
        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh Token도 만료된 경우
        console.error('Refresh Token이 만료되었습니다. 재로그인이 필요합니다.');
        processQueue(refreshError, null);
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### 사용 예시

```javascript
// src/components/ItemList.jsx
import apiClient from '../api/axios';

const fetchItems = async () => {
  try {
    const response = await apiClient.get('/api/web/item/');
    console.log('품목 목록:', response.data);
  } catch (error) {
    console.error('API 호출 실패:', error);
  }
};
```

---

## 🌐 Fetch API 구현

Axios를 사용하지 않는 경우 Fetch API로 구현할 수 있습니다.

```javascript
// src/api/fetch.js
const API_BASE_URL = 'http://localhost:8000';

let accessToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const refreshAccessToken = async () => {
  const response = await fetch(`${API_BASE_URL}/api/web/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh_token: refreshToken,
    }),
  });

  if (!response.ok) {
    throw new Error('Refresh Token이 만료되었습니다.');
  }

  const data = await response.json();
  accessToken = data.access_token;
  refreshToken = data.refresh_token;
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);

  return accessToken;
};

const apiFetch = async (url, options = {}) => {
  // Access Token 추가
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  let response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  // 401 에러 시 토큰 갱신
  if (response.status === 401) {
    if (isRefreshing) {
      // 이미 갱신 중이면 대기
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        headers['Authorization'] = `Bearer ${token}`;
        return fetch(`${API_BASE_URL}${url}`, {
          ...options,
          headers,
        });
      });
    }

    isRefreshing = true;

    try {
      const newToken = await refreshAccessToken();
      processQueue(null, newToken);

      // 원래 요청 재시도
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers,
      });
    } catch (error) {
      processQueue(error, null);
      localStorage.clear();
      window.location.href = '/login';
      throw error;
    } finally {
      isRefreshing = false;
    }
  }

  return response;
};

export default apiFetch;
```

### 사용 예시

```javascript
import apiFetch from '../api/fetch';

const fetchItems = async () => {
  try {
    const response = await apiFetch('/api/web/item/');
    const data = await response.json();
    console.log('품목 목록:', data);
  } catch (error) {
    console.error('API 호출 실패:', error);
  }
};
```

---

## ⚛️ React 구현 예시

### 1. Context API로 토큰 관리

```javascript
// src/context/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [accessToken, setAccessToken] = useState(localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refresh_token'));
  const [user, setUser] = useState(null);

  const login = async (loginId, password) => {
    const response = await axios.post('http://localhost:8000/api/web/auth/login', {
      loginId,
      password,
    });

    const { access_token, refresh_token, user } = response.data;
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    setUser(user);
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
  };

  const logout = () => {
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.clear();
  };

  const refreshAccessToken = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/web/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: new_refresh_token } = response.data;
      setAccessToken(access_token);
      setRefreshToken(new_refresh_token);
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', new_refresh_token);

      return access_token;
    } catch (error) {
      logout();
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        refreshToken,
        user,
        login,
        logout,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### 2. Custom Hook으로 API 호출

```javascript
// src/hooks/useApi.js
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/axios';

export const useApi = () => {
  const { accessToken, refreshAccessToken } = useAuth();

  const callApi = async (method, url, data = null) => {
    try {
      const config = {
        method,
        url,
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      };

      if (data) {
        config.data = data;
      }

      const response = await apiClient(config);
      return response.data;
    } catch (error) {
      if (error.response?.status === 401) {
        // 토큰 갱신 시도
        await refreshAccessToken();
        // 재시도는 Axios Interceptor가 처리
      }
      throw error;
    }
  };

  return { callApi };
};
```

### 3. 컴포넌트에서 사용

```javascript
// src/components/ItemList.jsx
import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';

const ItemList = () => {
  const [items, setItems] = useState([]);
  const { callApi } = useApi();

  useEffect(() => {
    const fetchItems = async () => {
      try {
        const data = await callApi('GET', '/api/web/item/');
        setItems(data.items);
      } catch (error) {
        console.error('품목 조회 실패:', error);
      }
    };

    fetchItems();
  }, []);

  return (
    <div>
      <h1>품목 목록</h1>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.itemName}</li>
        ))}
      </ul>
    </div>
  );
};

export default ItemList;
```

---

## 🖖 Vue.js 구현 예시

### 1. Axios Plugin 설정

```javascript
// src/plugins/axios.js
import axios from 'axios';
import router from '../router';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        localStorage.clear();
        router.push('/login');
        return Promise.reject(error);
      }

      try {
        const response = await axios.post('http://localhost:8000/api/web/auth/refresh', {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: new_refresh_token } = response.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', new_refresh_token);

        processQueue(null, access_token);

        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.clear();
        router.push('/login');
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### 2. Vuex Store

```javascript
// src/store/auth.js
import apiClient from '../plugins/axios';

export default {
  namespaced: true,
  state: {
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    user: null,
  },
  mutations: {
    SET_TOKENS(state, { accessToken, refreshToken }) {
      state.accessToken = accessToken;
      state.refreshToken = refreshToken;
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
    },
    SET_USER(state, user) {
      state.user = user;
    },
    LOGOUT(state) {
      state.accessToken = null;
      state.refreshToken = null;
      state.user = null;
      localStorage.clear();
    },
  },
  actions: {
    async login({ commit }, { loginId, password }) {
      const response = await apiClient.post('/api/web/auth/login', {
        loginId,
        password,
      });

      const { access_token, refresh_token, user } = response.data;
      commit('SET_TOKENS', {
        accessToken: access_token,
        refreshToken: refresh_token,
      });
      commit('SET_USER', user);
    },
    logout({ commit }) {
      commit('LOGOUT');
    },
  },
};
```

---

## 🔍 테스트 방법

### 1. 토큰 만료 시뮬레이션

```javascript
// Access Token을 짧게 설정 (백엔드 .env)
ACCESS_TOKEN_EXPIRE_MINUTES=1  // 1분

// 1분 후 API 호출 → 자동 갱신 확인
```

### 2. 콘솔 로그 확인

```javascript
// Axios Interceptor에 로그 추가
console.log('🔄 토큰 갱신 시도...');
console.log('✅ 토큰 갱신 성공:', access_token);
console.log('🔁 원래 요청 재시도:', originalRequest.url);
```

---

## ⚠️ 주의사항

### 1. **동시 요청 처리**
- 여러 API가 동시에 401을 받으면 토큰 갱신이 중복 실행될 수 있음
- `isRefreshing` 플래그와 `failedQueue`로 해결

### 2. **무한 루프 방지**
- `originalRequest._retry` 플래그로 재시도 1회만 허용

### 3. **Refresh Token 만료**
- Refresh Token도 만료되면 로그인 페이지로 리다이렉트

### 4. **보안**
- Refresh Token은 HttpOnly Cookie에 저장 권장 (XSS 방지)
- Access Token은 메모리에만 저장 권장

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24  
**버전**: 1.0.0

