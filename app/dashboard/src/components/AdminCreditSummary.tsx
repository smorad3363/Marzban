import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  HStack,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { AccountSummary } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const roleLabels: Record<string, string> = {
  OWNER: "مالک",
  SUPER_ADMIN: "ادمین ارشد",
  ADMIN: "ادمین",
};
const accountStatusLabels: Record<string, string> = {
  ACTIVE: "فعال",
  SUSPENDED: "متوقف",
  FROZEN: "مسدود",
};
const creationModeLabels: Record<string, string> = {
  PLAN_ONLY: "فقط با پلن",
  LEGACY_COMPAT: "حالت قدیمی",
};

export const AdminCreditSummary: FC = () => {
  const { getUserIsPending } = useGetUser();
  const query = useQuery<AccountSummary, Error>("account-summary", () => fetch("/account/summary"), {
    enabled: !getUserIsPending,
    refetchInterval: 15000,
  });

  if (getUserIsPending || query.isLoading) return <Skeleton height="132px" borderRadius="16px" mb={5} />;
  if (query.isError || !query.data) return <Alert status="error" borderRadius="12px" mb={5}><AlertIcon />اطلاعات حساب بارگذاری نشد.</Alert>;

  const account = query.data;
  const seatMode = account.billing_mode === "SEAT_CREDIT";
  const creditValue = (value: number | null) => value === null
    ? "نامحدود"
    : seatMode ? `${value} دستگاه` : String(formatBytes(value));
  const used = account.own_spend + account.delegated_traffic;
  const percent = account.total_traffic && account.total_traffic > 0
    ? Math.min(100, Math.round((used / account.total_traffic) * 100))
    : null;

  return (
    <Stack spacing={3} mb={5}>
      {account.account_status !== "ACTIVE" && (
        <Alert status="warning" borderRadius="12px" borderWidth="1px">
          <AlertIcon />این حساب فقط قابل مشاهده است. دلیل: {account.suspended_reason || account.account_status}
        </Alert>
      )}
      <Card bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="16px" boxShadow="panel" overflow="hidden">
        <HStack px={{ base: 4, md: 5 }} py={3} spacing={2} flexWrap="wrap" borderBottomWidth="1px" borderColor="#33483b">
          <Text fontSize="sm" fontWeight="750" me={1}>وضعیت حساب</Text>
          <Badge colorScheme={account.role === "OWNER" ? "purple" : account.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{roleLabels[account.role] || account.role}</Badge>
          <Badge colorScheme={account.account_status === "ACTIVE" ? "green" : "orange"}>{accountStatusLabels[account.account_status] || account.account_status}</Badge>
          <Badge colorScheme={account.user_creation_mode === "PLAN_ONLY" ? "blue" : "gray"}>{creationModeLabels[account.user_creation_mode] || account.user_creation_mode}</Badge>
        </HStack>
        <SimpleGrid columns={{ base: 1, md: 3 }}>
          <Box p={{ base: 4, md: 5 }} borderInlineEndWidth={{ base: 0, md: "1px" }} borderColor="#33483b">
            <Text color="primary.300" fontSize="xs" fontWeight="750">اعتبار باقی‌مانده</Text>
            <Text color="white" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={2} sx={{ fontVariantNumeric: "tabular-nums" }}>{creditValue(account.available_traffic)}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>مصرف خودتان {creditValue(account.own_spend)} · اعتبار داده‌شده {creditValue(account.delegated_traffic)}</Text>
            {percent !== null && <HStack mt={4}><Progress value={percent} colorScheme={percent >= 80 ? "orange" : "green"} size="sm" borderRadius="full" flex={1} aria-label="درصد مصرف اعتبار" /><Text color="gray.300" fontSize="xs">{percent}%</Text></HStack>}
          </Box>
          <Box p={{ base: 4, md: 5 }} borderTopWidth={{ base: "1px", md: 0 }} borderInlineEndWidth={{ base: 0, md: "1px" }} borderColor="#33483b">
            <Text color="gray.400" fontSize="xs" fontWeight="650">کاربران زیرمجموعه</Text>
            <Text color="white" fontSize="2xl" fontWeight="800" mt={2}>{account.subtree_users}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>{account.own_users} مستقیم · {account.subtree_users} با زیرمجموعه‌ها</Text>
          </Box>
          <Box p={{ base: 4, md: 5 }} borderTopWidth={{ base: "1px", md: 0 }} borderColor="#33483b">
            <Text color="gray.400" fontSize="xs" fontWeight="650">دفعات تمدید باقی‌مانده</Text>
            <Text color="white" fontSize="2xl" fontWeight="800" mt={2}>{account.renewal_remaining === null ? "نامحدود" : String(account.renewal_remaining)}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>{account.renewal_enabled ? "تمدید فعال است" : "تمدید بسته است"}</Text>
          </Box>
        </SimpleGrid>
      </Card>
    </Stack>
  );
};
