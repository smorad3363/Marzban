import { Alert, AlertIcon, Badge, Box, Button, Card, HStack, Progress, SimpleGrid, Skeleton, Stack, Text } from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { DashboardOverview as DashboardOverviewData } from "types/Dashboard";
import { formatBytes } from "utils/formatByte";

const Kpi: FC<{ label: string; value: string; detail: string; priority?: boolean }> = ({ label, value, detail, priority = false }) => (
  <Card
    p={{ base: 4, md: priority ? 5 : 4 }}
    bg={priority ? "#111d17" : "#0d1812"}
    color="gray.100"
    borderWidth="1px"
    borderColor={priority ? "rgba(72, 213, 139, .34)" : "#33483b"}
    borderRadius="16px"
    boxShadow={priority ? "panel" : "none"}
    minH={priority ? "148px" : "120px"}
  >
    <Text color="gray.300" fontSize="sm" fontWeight="600">{label}</Text>
    <Text mt={2} fontSize={priority ? { base: "2xl", md: "3xl" } : "2xl"} fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{value}</Text>
    <Text mt={1} color="gray.400" fontSize="xs">{detail}</Text>
  </Card>
);

const SectionTitle: FC<{ eyebrow: string; title: string; description: string }> = ({ eyebrow, title, description }) => (
  <Box>
    <Text color="primary.300" fontSize="xs" fontWeight="800">{eyebrow}</Text>
    <Text as="h2" mt={1} fontSize="lg" fontWeight="800">{title}</Text>
    <Text mt={1} color="gray.400" fontSize="sm">{description}</Text>
  </Box>
);

const billingModeLabels: Record<string, string> = {
  LEGACY_COMPAT: "حالت قدیمی",
  SEAT_CREDIT: "اعتبار دستگاه",
  USED_TRAFFIC: "مصرف واقعی",
  ALLOCATED_TRAFFIC: "حجم اختصاصی",
};

export const DashboardOverview: FC = () => {
  const { getUserIsPending } = useGetUser();
  const timezoneOffset = -new Date().getTimezoneOffset();
  const query = useQuery<DashboardOverviewData, Error>(
    ["dashboard-overview", timezoneOffset],
    () => fetch(`/dashboard/overview?timezone_offset_minutes=${timezoneOffset}`),
    { enabled: !getUserIsPending, refetchInterval: 30000 }
  );
  if (getUserIsPending || query.isLoading) return <Skeleton height="420px" borderRadius="16px" mb={5} />;
  if (query.isError || !query.data) return <Alert status="error" mb={5} borderRadius="12px"><AlertIcon />آمار داشبورد بارگذاری نشد.<Button ms="auto" minH="44px" onClick={() => query.refetch()}>تلاش دوباره</Button></Alert>;
  const data = query.data;
  const trend = data.new_users.change_percent === null ? "شروع مقایسه" : `${data.new_users.change_percent >= 0 ? "+" : ""}${data.new_users.change_percent}%`;
  return (
    <Stack spacing={6} mb={6} aria-live="polite">
      <Box as="section" aria-labelledby="dashboard-kpis-title">
        <Box id="dashboard-kpis-title"><SectionTitle eyebrow="آمار کلی" title="کاربران و مصرف" description="مهم‌ترین عددها برای یک بررسی سریع." /></Box>
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={4} mt={3}>
          <Kpi priority label="کل کاربران" value={String(data.total_users)} detail={`${data.active_users} فعال · ${data.online_users} آنلاین`} />
          <Kpi priority label="حجم مصرف‌شده" value={String(formatBytes(data.current_used_traffic))} detail={`${formatBytes(data.allocated_quota)} حجم تخصیص‌یافته`} />
        </SimpleGrid>
      </Box>

      <Box as="section" aria-labelledby="dashboard-trends-title">
        <Box id="dashboard-trends-title"><SectionTitle eyebrow="این هفته" title="تغییرات و هشدارها" description="کاربران جدید و حساب‌هایی که باید بررسی شوند." /></Box>
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={3}>
          <Kpi label="کاربران جدید این هفته" value={String(data.new_users.current)} detail={`${trend} · هفته قبل ${data.new_users.previous}`} />
          <Kpi label="نیازمند بررسی" value={String(data.disabled_users + data.expired_users + data.limited_users)} detail={`${data.on_hold_users} مورد در انتظار بررسی`} />
        </SimpleGrid>
      </Box>

      <Box as="section" aria-labelledby="dashboard-breakdown-title">
        <Box id="dashboard-breakdown-title"><SectionTitle eyebrow="نوع اعتبار" title="کاربران بر اساس نوع اعتبار" description="تعداد کاربر و میزان مصرف در هر نوع اعتبار." /></Box>
        <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} gap={3} mt={3}>
          {data.billing_modes.map((mode) => {
            const activePercent = mode.user_count ? Math.round((mode.active_users / mode.user_count) * 100) : 0;
            return <Card key={mode.billing_mode} p={4} bg="#0d1812" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="14px">
              <HStack justify="space-between"><Badge variant="subtle" colorScheme="green">{billingModeLabels[mode.billing_mode] || mode.billing_mode}</Badge><Text fontSize="xs" color="gray.400">{mode.admin_count} ادمین</Text></HStack>
              <Text mt={3} fontSize="xl" fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{mode.user_count} کاربر</Text>
              <Progress mt={3} value={activePercent} colorScheme="green" borderRadius="full" aria-label={`کاربران فعال ${billingModeLabels[mode.billing_mode] || mode.billing_mode}`} />
              <Text mt={2} fontSize="xs" color="gray.400">{mode.active_users} فعال · {formatBytes(mode.current_used_traffic)} مصرف</Text>
            </Card>;
          })}
        </SimpleGrid>
      </Box>
    </Stack>
  );
};
