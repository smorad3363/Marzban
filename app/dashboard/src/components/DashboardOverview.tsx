import { Alert, AlertIcon, Badge, Box, Button, Card, HStack, IconButton, SimpleGrid, Skeleton, Stack, Text, chakra } from "@chakra-ui/react";
import {
  BoltIcon, ChartBarIcon, Cog6ToothIcon, RectangleStackIcon, ShieldCheckIcon,
  UserGroupIcon, UserPlusIcon, UsersIcon,
} from "@heroicons/react/24/outline";
import type { ApexOptions } from "apexcharts";
import useGetUser from "hooks/useGetUser";
import { FC, ReactElement, useMemo, useState } from "react";
import Chart from "react-apexcharts";
import { useQuery } from "react-query";
import { useNavigate } from "react-router-dom";
import { fetch } from "service/http";
import { AccountSummary, AdminCapabilities } from "types/Admin";
import { DashboardOverview as DashboardOverviewData } from "types/Dashboard";
import { formatBytes } from "utils/formatByte";
import { useDashboard } from "contexts/DashboardContext";

const iconStyle = { baseStyle: { w: 6, h: 6 } };
const UsersKpiIcon = chakra(UsersIcon, iconStyle);
const OnlineIcon = chakra(BoltIcon, iconStyle);
const TrafficIcon = chakra(ChartBarIcon, iconStyle);
const ReviewIcon = chakra(ShieldCheckIcon, iconStyle);

const billingModeLabels: Record<string, string> = {
  LEGACY_COMPAT: "قدیمی",
  SEAT_CREDIT: "ظرفیت دستگاه قدیمی",
  USED_TRAFFIC: "مصرف واقعی",
  ALLOCATED_TRAFFIC: "حجم ساخته‌شده",
  USER_CREDIT: "نامحدود · سقف اکانت",
};

const Kpi: FC<{ label: string; value: string; detail: string; icon: ReactElement }> = ({ label, value, detail, icon }) => (
  <Card p={3} bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px">
    <HStack justify="space-between" align="start">
      <Box><Text color="gray.300" fontSize="xs" fontWeight="650">{label}</Text><Text mt={0.5} fontSize="xl" fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{value}</Text></Box>
      <Box p={2} color="primary.300" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px">{icon}</Box>
    </HStack>
    <Text mt={1.5} color="gray.400" fontSize="xs">{detail}</Text>
  </Card>
);

const QuickAction: FC<{ label: string; icon: ReactElement; onClick: () => void }> = ({ label, icon, onClick }) => (
  <Button minH="42px" h="auto" px={3} variant="outline" borderColor="var(--panel-border)" bg="var(--panel-surface)" gap={2} fontSize="xs" justifyContent="flex-start" _hover={{ borderColor: "primary.400", color: "primary.200" }} onClick={onClick}>
    <Box color="primary.300">{icon}</Box><Text>{label}</Text>
  </Button>
);

export const DashboardOverview: FC = () => {
  const { userData, getUserIsPending, getUserIsSuccess } = useGetUser();
  const navigate = useNavigate();
  const [quickOpen, setQuickOpen] = useState(false);
  const timezoneOffset = -new Date().getTimezoneOffset();
  const query = useQuery<DashboardOverviewData, Error>(["dashboard-overview", timezoneOffset], () => fetch(`/dashboard/overview?timezone_offset_minutes=${timezoneOffset}`), { enabled: !getUserIsPending, refetchInterval: 30000 });
  const capabilities = useQuery<AdminCapabilities, Error>(["admin-capabilities", userData.username], () => fetch("/admin/capabilities"), { enabled: getUserIsSuccess });
  const account = useQuery<AccountSummary, Error>(["account-summary", userData.username], () => fetch("/account/summary"), { enabled: getUserIsSuccess });
  const data = query.data;
  const chartText = "#a8b0aa";
  const barOptions = useMemo<ApexOptions>(() => ({
    chart: { toolbar: { show: false }, background: "transparent", fontFamily: "Vazirmatn" },
    colors: ["#d7ad54"], dataLabels: { enabled: false }, grid: { borderColor: "rgba(148,163,184,.10)" },
    plotOptions: { bar: { borderRadius: 4, columnWidth: "46%" } },
    xaxis: { categories: data?.billing_modes.map((item) => billingModeLabels[item.billing_mode] || item.billing_mode) || [], labels: { style: { colors: chartText, fontSize: "10px" } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { colors: chartText }, formatter: (value) => `${Math.round(value)} GB` } },
    tooltip: { theme: "dark" },
  }), [data]);
  const donutOptions = useMemo<ApexOptions>(() => ({
    chart: { background: "transparent", fontFamily: "Vazirmatn" }, colors: ["#35c879", "#d7ad54", "#ef6b65"],
    labels: ["فعال", "در انتظار", "نیازمند بررسی"], legend: { position: "bottom", labels: { colors: chartText } },
    dataLabels: { enabled: false }, stroke: { width: 0 }, plotOptions: { pie: { donut: { size: "72%" } } }, tooltip: { theme: "dark" },
  }), []);

  if (getUserIsPending || query.isLoading) return <Skeleton height="420px" borderRadius="16px" mb={5} />;
  if (query.isError || !data) return <Alert status="error" mb={5} borderRadius="12px"><AlertIcon />آمار داشبورد بارگذاری نشد.<Button ms="auto" minH="40px" onClick={() => query.refetch()}>تلاش دوباره</Button></Alert>;
  const reviewCount = data.disabled_users + data.expired_users + data.limited_users;
  const trend = data.new_users.change_percent === null ? "شروع مقایسه" : `${data.new_users.change_percent >= 0 ? "+" : ""}${data.new_users.change_percent}% نسبت به هفته قبل`;
  return (
    <Stack spacing={4} mb={5} aria-live="polite">
      <SimpleGrid columns={{ base: 1, sm: 2, xl: 4 }} gap={3}>
        <Kpi label="کل کاربران" value={String(data.total_users)} detail={`${data.new_users.current} کاربر جدید · ${trend}`} icon={<UsersKpiIcon />} />
        <Kpi label="کاربران آنلاین" value={String(data.online_users)} detail={`${data.active_users} حساب فعال`} icon={<OnlineIcon />} />
        <Kpi label="مصرف ثبت‌شده" value={String(formatBytes(data.current_used_traffic))} detail={`${formatBytes(data.allocated_quota)} حجم ساخته‌شده`} icon={<TrafficIcon />} />
        <Kpi label="نیازمند بررسی" value={String(reviewCount)} detail={`${data.on_hold_users} حساب در انتظار`} icon={<ReviewIcon />} />
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, xl: 3 }} gap={3}>
        <Card p={3} bg="var(--panel-surface)" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px" minW={0} gridColumn={{ xl: "span 2" }}>
          <HStack justify="space-between"><Text fontWeight="800">مصرف نوع‌های اعتبار</Text><Badge colorScheme="yellow">گیگابایت</Badge></HStack>
          <Box h={{ base: "165px", md: "190px" }} dir="ltr"><Chart type="bar" height="100%" options={barOptions} series={[{ name: "مصرف", data: data.billing_modes.map((item) => Number((item.current_used_traffic / 1073741824).toFixed(2))) }]} /></Box>
        </Card>
        <Card p={3} bg="var(--panel-surface)" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px" minW={0}>
          <Text fontWeight="800">وضعیت کاربران</Text>
          <Box h={{ base: "165px", md: "190px" }} dir="ltr"><Chart type="donut" height="100%" options={donutOptions} series={[data.active_users, data.on_hold_users, reviewCount]} /></Box>
        </Card>
      </SimpleGrid>

      <Box position="fixed" insetInlineEnd={{ base: 4, md: 6 }} bottom={{ base: 4, md: 6 }} zIndex="popover">
        {quickOpen && <Stack mb={2} p={2} minW="190px" bg="var(--panel-nested)" borderWidth="1px" borderColor="var(--panel-border-strong)" borderRadius="14px" boxShadow="0 18px 48px rgba(0,0,0,.5)">
          {account.data?.user_creation_mode === "FREE_FORM"
            ? <QuickAction label="افزودن کاربر" icon={<UserPlusIcon width={25} />} onClick={() => useDashboard.getState().onCreateUser(true)} />
            : <QuickAction label="ساخت کاربر از پلن" icon={<UserPlusIcon width={25} />} onClick={() => navigate("/plans/")} />}
          <QuickAction label="فهرست کاربران" icon={<UsersIcon width={25} />} onClick={() => { window.dispatchEvent(new Event("open-users-panel")); window.setTimeout(() => document.getElementById("user-operations-title")?.scrollIntoView({ behavior: "smooth" }), 0); setQuickOpen(false); }} />
          {capabilities.data?.can_create_admins && <QuickAction label="افزودن ادمین" icon={<UserGroupIcon width={25} />} onClick={() => navigate("/admins/?create=1")} />}
          {capabilities.data?.can_manage_admins && <QuickAction label="مدیریت ادمین‌ها" icon={<ShieldCheckIcon width={25} />} onClick={() => navigate("/admins/")} />}
          <QuickAction label="پلن‌ها" icon={<RectangleStackIcon width={25} />} onClick={() => navigate("/plans/")} />
          {(userData.role === "OWNER" || userData.is_sudo) && <QuickAction label="تنظیمات" icon={<Cog6ToothIcon width={25} />} onClick={() => useDashboard.setState({ isEditingCore: true })} />}
        </Stack>}
        <IconButton aria-label={quickOpen ? "بستن دسترسی سریع" : "بازکردن دسترسی سریع"} aria-expanded={quickOpen} icon={<BoltIcon width={24} />} onClick={() => setQuickOpen((value) => !value)} boxSize="54px" borderRadius="full" colorScheme="primary" color="#07130e" boxShadow="0 12px 30px rgba(0,0,0,.45)" />
      </Box>
    </Stack>
  );
};
