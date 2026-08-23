import {
  Alert,
  AlertIcon,
  Badge,
  Card,
  HStack,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC, PropsWithChildren } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { AccountSummary } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const SummaryCard: FC<PropsWithChildren<{ label: string; value: string; detail: string }>> = ({ label, value, detail, children }) => (
  <Card p={{ base: 4, md: 5 }} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="16px" boxShadow="panel">
    <Text color="gray.300" fontSize="sm" fontWeight="600">{label}</Text>
    <Text color="white" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={2} sx={{ fontVariantNumeric: "tabular-nums" }}>{value}</Text>
    <Text color="gray.400" fontSize="xs" mt={2}>{detail}</Text>
    {children}
  </Card>
);

export const AdminCreditSummary: FC = () => {
  const { getUserIsPending } = useGetUser();
  const query = useQuery<AccountSummary, Error>("account-summary", () => fetch("/account/summary"), {
    enabled: !getUserIsPending,
    refetchInterval: 15000,
  });

  if (getUserIsPending || query.isLoading) return <Skeleton height="132px" borderRadius="16px" mb={5} />;
  if (query.isError || !query.data) return <Alert status="error" borderRadius="12px" mb={5}><AlertIcon />خلاصه حساب دریافت نشد.</Alert>;

  const account = query.data;
  const seatMode = account.billing_mode === "SEAT_CREDIT";
  const creditValue = (value: number | null) => value === null
    ? "نامحدود"
    : seatMode ? `${value} seats` : String(formatBytes(value));
  const used = account.own_spend + account.delegated_traffic;
  const percent = account.total_traffic && account.total_traffic > 0
    ? Math.min(100, Math.round((used / account.total_traffic) * 100))
    : null;

  return (
    <Stack spacing={3} mb={5}>
      {account.account_status !== "ACTIVE" && (
        <Alert status="warning" borderRadius="12px" borderWidth="1px">
          <AlertIcon />این حساب در حالت فقط‌خواندنی است. دلیل: {account.suspended_reason || account.account_status}
        </Alert>
      )}
      <HStack spacing={2} flexWrap="wrap">
        <Badge colorScheme={account.role === "OWNER" ? "purple" : account.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{account.role.replace("_", " ")}</Badge>
        <Badge colorScheme={account.account_status === "ACTIVE" ? "green" : "orange"}>{account.account_status}</Badge>
        <Badge colorScheme={account.user_creation_mode === "PLAN_ONLY" ? "blue" : "gray"}>{account.user_creation_mode}</Badge>
      </HStack>
      <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
        <SummaryCard label="اعتبار قابل استفاده" value={creditValue(account.available_traffic)} detail={`مصرف مستقیم ${creditValue(account.own_spend)} · واگذاری ${creditValue(account.delegated_traffic)}`}>
          {percent !== null && <HStack mt={4}><Progress value={percent} colorScheme={percent >= 80 ? "orange" : "green"} size="sm" borderRadius="full" flex={1} aria-label="درصد مصرف اعتبار" /><Text color="gray.300" fontSize="xs">{percent}%</Text></HStack>}
        </SummaryCard>
        <SummaryCard label="کاربران" value={String(account.subtree_users)} detail={`${account.own_users} کاربر مستقیم · ${account.subtree_users} کاربر در کل زیرشاخه`} />
        <SummaryCard label="تمدید باقی‌مانده" value={account.renewal_remaining === null ? "نامحدود" : String(account.renewal_remaining)} detail={account.renewal_enabled ? "تمدید مجاز است" : "تمدید غیرفعال است"} />
      </SimpleGrid>
    </Stack>
  );
};
