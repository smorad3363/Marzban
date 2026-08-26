import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  HStack,
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

const roleLabels: Record<string, string> = {
  OWNER: "مالک",
  ADMIN: "ادمین",
};
const accountStatusLabels: Record<string, string> = {
  ACTIVE: "فعال",
  SUSPENDED: "متوقف",
  FROZEN: "مسدود",
};
const creationModeLabels: Record<string, string> = {
  FREE_FORM: "ساخت آزاد",
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

  return (
    <Stack spacing={3} mb={5}>
      {account.account_status !== "ACTIVE" && (
        <Alert status="warning" borderRadius="12px" borderWidth="1px">
          <AlertIcon />این حساب فقط قابل مشاهده است. دلیل: {account.suspended_reason || account.account_status}
        </Alert>
      )}
      <Card bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="16px" boxShadow="panel" overflow="hidden">
        <HStack px={{ base: 4, md: 5 }} py={3} spacing={2} flexWrap="wrap" borderBottomWidth="1px" borderColor="#33483b">
          <Text fontSize="sm" fontWeight="750" me={1}>وضعیت حساب</Text>
          <Badge colorScheme={account.role === "OWNER" ? "purple" : "gray"}>{roleLabels[account.role] || account.role}</Badge>
          <Badge colorScheme={account.account_status === "ACTIVE" ? "green" : "orange"}>{accountStatusLabels[account.account_status] || account.account_status}</Badge>
          <Badge colorScheme={account.user_creation_mode === "PLAN_ONLY" ? "blue" : "gray"}>{creationModeLabels[account.user_creation_mode] || account.user_creation_mode}</Badge>
        </HStack>
        <SimpleGrid columns={{ base: 1, md: 3 }}>
          <Box p={{ base: 4, md: 5 }} borderInlineEndWidth={{ base: 0, md: "1px" }} borderColor="#33483b">
            <Text color="primary.300" fontSize="xs" fontWeight="750">اعتبار مالی</Text>
            <Text color="white" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={2} sx={{ fontVariantNumeric: "tabular-nums" }}>{account.role === "OWNER" ? "بدون سقف" : `${account.money_balance_toman.toLocaleString("fa-IR")} تومان`}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>{account.billing_mode === "USED_TRAFFIC" ? `قیمت خرید هر گیگ: ${(account.used_traffic_price_per_gib_toman || 0).toLocaleString("fa-IR")} تومان` : "هر ساخت یا تمدید، قیمت همان پلن را از کیف پول کم می‌کند."}</Text>
          </Box>
          <Box p={{ base: 4, md: 5 }} borderTopWidth={{ base: "1px", md: 0 }} borderInlineEndWidth={{ base: 0, md: "1px" }} borderColor="#33483b">
            <Text color="gray.400" fontSize="xs" fontWeight="650">کاربران زیرمجموعه</Text>
            <Text color="white" fontSize="2xl" fontWeight="800" mt={2}>{account.subtree_users}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>{account.own_users} مستقیم · {account.subtree_users} با زیرمجموعه‌ها</Text>
          </Box>
          <Box p={{ base: 4, md: 5 }} borderTopWidth={{ base: "1px", md: 0 }} borderColor="#33483b">
            <Text color="gray.400" fontSize="xs" fontWeight="650">اعتبار تمدید باقی‌مانده</Text>
            <Text color="white" fontSize="2xl" fontWeight="800" mt={2}>{account.renewal_remaining === null ? "نامحدود" : String(account.renewal_remaining)}</Text>
            <Text color="gray.400" fontSize="xs" mt={2}>{account.renewal_enabled ? "تمدید فعال است" : "تمدید بسته است"}</Text>
          </Box>
        </SimpleGrid>
      </Card>
    </Stack>
  );
};
