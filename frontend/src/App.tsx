import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout, Button, Tooltip } from 'antd';
import { SunOutlined, MoonOutlined, CheckCircleFilled } from '@ant-design/icons';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import MatchTest from './pages/MatchTest';
import LexiconMgmt from './pages/LexiconMgmt';
import StandardItems from './pages/StandardItems';
import UnmatchedWorkbench from './pages/UnmatchedWorkbench';

const { Header, Content } = Layout;

const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark' ||
      (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
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
    <BrowserRouter>
      <Layout className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans transition-colors duration-200">
        <Sidebar />
        <Layout className="bg-transparent flex flex-col min-h-screen">
          <Header className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md px-6 border-b border-zinc-200/80 dark:border-zinc-800 flex items-center justify-between sticky top-0 z-10 shadow-xs h-16">
            <div className="flex items-center gap-3">
              <h1 className="text-base font-bold text-zinc-900 dark:text-zinc-100 m-0 tracking-tight">
                MMS 标准化匹配服务管理平台
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50">
                <CheckCircleFilled className="text-emerald-500 text-[10px]" />
                引擎就绪
              </span>
            </div>

            <div className="flex items-center gap-3">
              <Tooltip title={darkMode ? '切换为浅色模式' : '切换为深色模式'}>
                <Button
                  type="text"
                  shape="circle"
                  icon={darkMode ? <SunOutlined className="text-amber-400 text-lg" /> : <MoonOutlined className="text-zinc-600 text-lg" />}
                  onClick={toggleDarkMode}
                  className="hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700"
                />
              </Tooltip>
            </div>
          </Header>
          <Content className="m-5 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 p-6 shadow-xs flex-1 flex flex-col overflow-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/match" element={<MatchTest />} />
              <Route path="/lexicon" element={<LexiconMgmt />} />
              <Route path="/standard-items" element={<StandardItems />} />
              <Route path="/check-standard-items" element={<StandardItems />} />
              <Route path="/unmatched" element={<UnmatchedWorkbench />} />

              <Route path="/agent" element={
                <div className="text-center py-24 space-y-2">
                  <h3 className="text-lg font-medium text-zinc-700 dark:text-zinc-300">AI 智能分析助手</h3>
                  <p className="text-sm text-zinc-400 dark:text-zinc-500">此模块正在打磨中，敬请期待规则优化建议与智能歧义诊断能力</p>
                </div>
              } />
              <Route path="/history" element={
                <div className="text-center py-24 space-y-2">
                  <h3 className="text-lg font-medium text-zinc-700 dark:text-zinc-300">版本变更日志</h3>
                  <p className="text-sm text-zinc-400 dark:text-zinc-500">规则引擎历史快照与词库版本追溯面板开发中</p>
                </div>
              } />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </BrowserRouter>
  );
};

export default App;

