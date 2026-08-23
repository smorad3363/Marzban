import { Alert, AlertIcon, Badge, Box, Button, Card, HStack, Progress, SimpleGrid, Skeleton, Stack, Text } from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { DashboardOverview as DashboardOverviewData } from "types/Dashboard";
import { formatBytes } from "utils/formatByte";

const Kpi: FC<{ label: string; value: string; detail: string }> = ({ label, value, detail }) => (
  <Card p={4} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="16px">
    <Text color="gray.300" fontSize="sm" fontWeight="600">{label}</Text>
    <Text mt={2} fontSize="2xl" fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{value}</Text>
    <Text mt={1} color="gray.400" fontSize="xs">{detail}</Text>
  </Card>
);

export const DashboardOverview: FC = () => {
  const { getUserIsPending } = useGetUser();
  const timezoneOffset = -new Date().getTimezoneOffset();
  const query = useQuery<DashboardOverviewData, Error>(
    ["dashboard-overview", timezoneOffset],
    () => fetch(`/dashboard/overview?timezone_offset_minutes=${timezoneOffset}`),
    { enabled: !getUserIsPending, refetchInterval: 30000 }
  );
  if (getUserIsPending || query.isLoading) return <Skeleton height="260px" borderRadius="16px" mb={5} />;
  if (query.isError || !query.data) return <Alert status="error" mb={5} borderRadius="12px"><AlertIcon />Dashboard metrics could not be loaded.<Button ms="auto" minH="44px" onClick={() => query.refetch()}>Retry</Button></Alert>;
  const data = query.data;
  const trend = data.new_users.change_percent === null ? "new baseline" : `${data.new_users.change_percent >= 0 ? "+" : ""}${data.new_users.change_percent}%`;
  return (
    <Stack spacing={4} mb={5} aria-live="polite">
      <SimpleGrid columns={{ base: 1, sm: 2, xl: 4 }} gap={4}>
        <Kpi label="Total users" value={String(data.total_users)} detail={`${data.active_users} active · ${data.online_users} online`} />
        <Kpi label="New this week" value={String(data.new_users.current)} detail={`${trend} · previous ${data.new_users.previous}`} />
        <Kpi label="Traffic used" value={String(formatBytes(data.current_used_traffic))} detail={`Allocated ${formatBytes(data.allocated_quota)}`} />
        <Kpi label="Attention" value={String(data.disabled_users + data.expired_users + data.limited_users)} detail={`${data.on_hold_users} on hold`} />
      </SimpleGrid>
      <Box>
        <Text fontWeight="750" mb={3}>Billing mode overview</Text>
        <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} gap={3}>
          {data.billing_modes.map((mode) => {
            const activePercent = mode.user_count ? Math.round((mode.active_users / mode.user_count) * 100) : 0;
            return <Card key={mode.billing_mode} p={4} bg="#0d1812" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="14px">
              <HStack justify="space-between"><Badge variant="subtle" colorScheme="green">{mode.billing_mode}</Badge><Text fontSize="xs" color="gray.400">{mode.admin_count} admins</Text></HStack>
              <Text mt={3} fontSize="xl" fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{mode.user_count} users</Text>
              <Progress mt={3} value={activePercent} colorScheme="green" borderRadius="full" aria-label={`${mode.billing_mode} active users`} />
              <Text mt={2} fontSize="xs" color="gray.400">{mode.active_users} active · {formatBytes(mode.current_used_traffic)} used</Text>
            </Card>;
          })}
        </SimpleGrid>
      </Box>
    </Stack>
  );
};
