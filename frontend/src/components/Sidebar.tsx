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

  const selectedKey = location.pathname === '/check-standard-items' ? '/standard-items' : location.pathname;

  return (
    <Sider
      width={220}
      theme="light"
      className="border-r border-zinc-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 select-none shadow-xs"
    >
      <div className="px-5 py-5 flex items-center gap-3 border-b border-zinc-100 dark:border-zinc-800/80">
        <div className="w-8 h-8 rounded-lg bg-blue-600 dark:bg-blue-700 flex items-center justify-center text-white shadow-xs">
          <MedicineBoxOutlined className="text-lg" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-none m-0">MMS Platform</h2>
          <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium">医学标准化引擎</span>
        </div>
      </div>
      <div className="py-3 px-2">
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="border-r-0 font-medium text-sm text-zinc-600 dark:text-zinc-400 space-y-1"
        />
      </div>
    </Sider>
  );

};

export default Sidebar;

