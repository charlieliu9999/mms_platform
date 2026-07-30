import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  DatabaseOutlined,
  CheckSquareOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
  HistoryOutlined,
  MedicineBoxOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '概览看板',
    },
    {
      key: '/match',
      icon: <SearchOutlined />,
      label: '匹配测试',
    },
    {
      key: '/lexicon',
      icon: <DatabaseOutlined />,
      label: '词库治理台',
    },
    {
      key: '/standard-items',
      icon: <CheckSquareOutlined />,
      label: '标准项目',
    },
    {
      key: '/unmatched',
      icon: <ExclamationCircleOutlined />,
      label: '未匹配工作台',
    },
    {
      key: '/evaluation',
      icon: <ExperimentOutlined />,
      label: '评测系统',
    },
    {
      key: '/agent',
      icon: <RobotOutlined />,
      label: 'AI 建议',
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: '版本历史',
    },
  ];

  const selectedKey = location.pathname === '/check-standard-items'
    ? '/standard-items'
    : location.pathname.startsWith('/evaluation')
    ? '/evaluation'
    : location.pathname;

  return (
    <Sider
      width={220}
      className="border-r select-none shadow-xs transition-colors duration-200 bg-bg-card border-border-theme"
    >
      <div className="px-5 py-5 flex items-center gap-3 border-b border-border-theme">
        <div className="w-8 h-8 rounded-xl bg-brand-color flex items-center justify-center text-white shadow-xs shrink-0">
          <MedicineBoxOutlined className="text-lg" />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-extrabold leading-none m-0 truncate text-text-primary">MMS Platform</h2>
          <span className="text-[10px] font-medium block mt-1 text-text-secondary">医学标准化引擎</span>
        </div>
      </div>
      <div className="py-3 px-2">
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="border-r-0 font-semibold text-xs space-y-1 bg-transparent"
        />
      </div>
    </Sider>
  );
};

export default Sidebar;
