import {
  Alert,
  AlertIcon,
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
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { AdminCapabilities } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const readableBytes = (value: number) => String(formatBytes(value));

const SummaryCard: FC<PropsWithChildren<{ label: string; value: string; detail: string }>> = ({
  label,
  value,
  detail,
  children,
}) => (
  <Card
    p={{ base: 4, md: 5 }}
    bg="#111d17"
    color="gray.100"
    borderWidth="1px"
    borderColor="#33483b"
    borderRadius="16px"
    boxShadow="panel"
  >
    <Text color="gray.300" fontSize="sm" fontWeight="600">{label}</Text>
    <Text color="white" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={2}>
      {value}
    </Text>
    <Text color="gray.400" fontSize="xs" mt={2}>{detail}</Text>
    {children}
  </Card>
);

export const AdminCreditSummary: FC = () => {
  const { t } = useTranslation();
  const { userData, getUserIsPending } = useGetUser();
  const query = useQuery<AdminCapabilities, Error>(
    ["admin-capabilities"],
    () => fetch("/admin/capabilities"),
    {
      enabled: !getUserIsPending && !userData.is_sudo,
      refetchInterval: 15000,
    }
  );

  if (getUserIsPending || userData.is_sudo) return null;
  if (query.isLoading) {
    return <Skeleton height="132px" borderRadius="16px" mb={5} />;
  }
  if (query.isError || !query.data) {
    return (
      <Alert status="error" borderRadius="12px" mb={5}>
        <AlertIcon />{t("adminCredit.loadFailed")}
      </Alert>
    );
  }

  const quota = query.data.quota;
  const remainingCredit = quota.credit_remaining === null
    ? t("unlimited")
    : readableBytes(quota.credit_remaining);
  const remainingOperations = quota.operation_allowance_remaining === null
    ? t("unlimited")
    : String(quota.operation_allowance_remaining);
  const creditDetail = quota.credit_limit === null
    ? t("adminCredit.noCreditLimit")
    : t("adminCredit.creditDetail", {
        used: readableBytes(quota.credit_used),
        limit: readableBytes(quota.credit_limit),
      });

  return (
    <Stack spacing={3} mb={5}>
      {quota.admin_warning_active && (
        <Alert status="warning" borderRadius="12px" borderWidth="1px">
          <AlertIcon />
          {t("adminCredit.warning", {
            percent: quota.credit_usage_percent,
            threshold: quota.admin_warning_percent,
          })}
        </Alert>
      )}
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
        <SummaryCard
          label={t("adminCredit.remainingCredit")}
          value={remainingCredit}
          detail={creditDetail}
        >
          {quota.credit_usage_percent !== null && (
            <HStack mt={4}>
              <Progress
                value={Math.min(quota.credit_usage_percent, 100)}
                colorScheme={quota.admin_warning_active ? "orange" : "green"}
                size="sm"
                borderRadius="full"
                flex={1}
                aria-label={t("adminCredit.usagePercent")}
              />
              <Text color="gray.300" fontSize="xs">{quota.credit_usage_percent}%</Text>
            </HStack>
          )}
        </SummaryCard>
        <SummaryCard
          label={t("adminCredit.remainingOperations")}
          value={remainingOperations}
          detail={t("adminCredit.operationsHelp")}
        />
      </SimpleGrid>
    </Stack>
  );
};
