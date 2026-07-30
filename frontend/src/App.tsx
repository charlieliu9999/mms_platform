import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout, ConfigProvider, theme } from 'antd';
import { SunOutlined, MoonOutlined, CheckCircleFilled } from '@ant-design/icons';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import MatchTest from './pages/MatchTest';
import LexiconMgmt from './pages/LexiconMgmt';
import StandardItems from './pages/StandardItems';
import UnmatchedWorkbench from './pages/UnmatchedWorkbench';
import EvaluationDashboard from './pages/Evaluation/Dashboard';
import CreateTask from './pages/Evaluation/CreateTask';
import TaskDetail from './pages/Evaluation/TaskDetail';

const { Header, Content } = Layout;

const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode(prev => !prev);
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#2563eb',
          colorBgLayout: 'var(--bg-base)',
          colorBgContainer: 'var(--bg-card)',
          colorBorderSecondary: 'var(--border-theme)',
          colorText: 'var(--text-primary)',
          colorTextDescription: 'var(--text-secondary)',
          borderRadius: 8,
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <Layout className="min-h-screen font-sans transition-colors duration-200 bg-bg-base text-text-primary">
          <Sidebar />
          <Layout className="bg-transparent flex flex-col min-h-screen">
            {/* Header 顶部导航栏 */}
            <Header className="px-6 border-b flex items-center justify-between sticky top-0 z-10 shadow-xs h-16 transition-colors duration-200 bg-bg-card border-border-theme">
              <div className="flex items-center gap-3">
                <h1 className="text-base font-extrabold m-0 tracking-tight text-text-primary">
                  MMS 标准化匹配服务管理平台
                </h1>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  darkMode ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/50' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}>
                  <CheckCircleFilled className="text-emerald-500 text-[10px]" />
                  引擎就绪
                </span>
              </div>

              {/* 明暗模式一键 Toggle 按键 */}
              <div className="flex items-center gap-3 select-none">
                <button
                  onClick={toggleDarkMode}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 border cursor-pointer ${
                    darkMode
                      ? 'bg-zinc-800 text-amber-300 border-zinc-700 hover:bg-zinc-700 shadow-sm'
                      : 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200 shadow-xs'
                  }`}
                  title={darkMode ? '切换为浅色商务模式' : '切换为深色夜间模式'}
                >
                  {darkMode ? (
                    <>
                      <MoonOutlined className="text-amber-400 text-sm" />
                      <span>深色模式</span>
                    </>
                  ) : (
                    <>
                      <SunOutlined className="text-amber-500 text-sm" />
                      <span>浅色模式</span>
                    </>
                  )}
                </button>
              </div>
            </Header>

            {/* Content 主内容容器 */}
            <Content className="m-5 rounded-2xl border p-6 shadow-xs flex-1 flex flex-col overflow-auto transition-colors duration-200 bg-bg-card border-border-theme">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/match" element={<MatchTest />} />
                <Route path="/lexicon" element={<LexiconMgmt />} />
                <Route path="/standard-items" element={<StandardItems />} />
                <Route path="/check-standard-items" element={<StandardItems />} />
                <Route path="/unmatched" element={<UnmatchedWorkbench />} />
                <Route path="/evaluation" element={<EvaluationDashboard />} />
                <Route path="/evaluation/create" element={<CreateTask />} />
                <Route path="/evaluation/tasks/:taskId" element={<TaskDetail />} />

                <Route path="/agent" element={
                  <div className="text-center py-24 space-y-2">
                    <h3 className="text-lg font-medium text-text-secondary">AI 智能分析助手</h3>
                    <p className="text-sm text-text-secondary">此模块正在打磨中，敬请期待规则优化建议与智能歧义诊断能力</p>
                  </div>
                } />
                <Route path="/history" element={
                  <div className="text-center py-24 space-y-2">
                    <h3 className="text-lg font-medium text-text-secondary">版本变更日志</h3>
                    <p className="text-sm text-text-secondary">规则引擎历史快照与词库版本追溯面板开发中</p>
                  </div>
                } />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
