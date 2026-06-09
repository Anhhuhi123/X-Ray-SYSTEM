"use client";

import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  BarChart, Bar
} from "recharts";

const requestData = [
  { name: "Mon", requests: 4000 },
  { name: "Tue", requests: 3000 },
  { name: "Wed", requests: 2000 },
  { name: "Thu", requests: 2780 },
  { name: "Fri", requests: 1890 },
  { name: "Sat", requests: 2390 },
  { name: "Sun", requests: 3490 },
];

const modelData = [
  { name: "GPT-4o", value: 400 },
  { name: "Claude 3.5 Sonnet", value: 300 },
  { name: "Gemini 1.5 Pro", value: 300 },
  { name: "Local Llama 3", value: 200 },
];
const COLORS = ["#3b82f6", "#f59e0b", "#10b981", "#8b5cf6"];

const activeUsersData = [
  { name: "00:00", users: 120 },
  { name: "04:00", users: 80 },
  { name: "08:00", users: 450 },
  { name: "12:00", users: 890 },
  { name: "16:00", users: 650 },
  { name: "20:00", users: 320 },
];

export function RequestTrendChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={requestData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
        <XAxis dataKey="name" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
        <RechartsTooltip 
          contentStyle={{ backgroundColor: "#171717", borderColor: "#262626", borderRadius: "8px", color: "#fff" }}
          itemStyle={{ color: "#fff" }}
        />
        <Line type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ModelUsageChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={modelData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {modelData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <RechartsTooltip 
          contentStyle={{ backgroundColor: "#171717", borderColor: "#262626", borderRadius: "8px", color: "#fff" }}
          itemStyle={{ color: "#fff" }}
        />
        <Legend verticalAlign="bottom" height={36} iconType="circle" />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ActiveUsersChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={activeUsersData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
        <XAxis dataKey="name" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
        <RechartsTooltip 
          contentStyle={{ backgroundColor: "#171717", borderColor: "#262626", borderRadius: "8px", color: "#fff" }}
          cursor={{ fill: '#262626' }}
        />
        <Bar dataKey="users" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
