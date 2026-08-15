import { Box, BoxProps, Card, chakra, HStack, SimpleGrid, Text } from "@chakra-ui/react";
import {
  ChartBarIcon,
  ChartPieIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import { useDashboard } from "contexts/DashboardContext";
import { FC, PropsWithChildren, ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { formatBytes, numberWithCommas } from "utils/formatByte";

const TotalUsersIcon = chakra(UsersIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    position: "relative",
    zIndex: "2",
  },
});

const NetworkIcon = chakra(ChartBarIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    position: "relative",
    zIndex: "2",
  },
});

const MemoryIcon = chakra(ChartPieIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    position: "relative",
    zIndex: "2",
  },
});

type StatisticCardProps = {
  title: string;
  content: ReactNode;
  icon: ReactElement;
};

const StatisticCard: FC<PropsWithChildren<StatisticCardProps>> = ({
  title,
  content,
  icon,
}) => {
  return (
    <Card
      p={{ base: 4, md: 5 }}
      borderWidth="1px"
      borderColor="gray.200"
      bg="white"
      _dark={{ borderColor: "whiteAlpha.200", bg: "surface.dark" }}
      borderStyle="solid"
      boxShadow="panel"
      borderRadius="18px"
      width="full"
      display="flex"
      justifyContent="space-between"
      flexDirection={{ base: "row", xl: "column" }}
      alignItems={{ base: "center", xl: "stretch" }}
      minH={{ xl: "154px" }}
    >
      <HStack alignItems="center" columnGap="4">
        <Box p="2.5" position="relative" color="primary.600" bg="primary.50" _dark={{ color: "primary.300", bg: "whiteAlpha.100" }} borderRadius="12px">
          {icon}
        </Box>
        <Text
          color="gray.600"
          _dark={{
            color: "gray.300",
          }}
          fontWeight="medium"
          textTransform="capitalize"
          fontSize="sm"
        >
          {title}
        </Text>
      </HStack>
      <Box fontSize={{ base: "2xl", xl: "3xl" }} fontWeight="800" letterSpacing="-0.035em" mt={{ base: 0, xl: 5 }}>
        {content}
      </Box>
    </Card>
  );
};
export const StatisticsQueryKey = "statistics-query-key";
export const Statistics: FC<BoxProps> = (props) => {
  const { version } = useDashboard();
  const { data: systemData } = useQuery({
    queryKey: StatisticsQueryKey,
    queryFn: () => fetch("/system"),
    refetchInterval: 5000,
    onSuccess: ({ version: currentVersion }) => {
      if (version !== currentVersion)
        useDashboard.setState({ version: currentVersion });
    },
  });
  const { t } = useTranslation();
  return (
    <SimpleGrid
      columns={{ base: 1, md: 3 }}
      gap={{ base: 3, md: 4 }}
      {...props}
    >
      <StatisticCard
        title={t("activeUsers")}
        content={
          systemData && (
            <HStack alignItems="flex-end">
              <Text>{numberWithCommas(systemData.users_active)}</Text>
              <Text
                fontWeight="normal"
                fontSize="lg"
                as="span"
                display="inline-block"
                pb="5px"
              >
                / {numberWithCommas(systemData.total_user)}
              </Text>
            </HStack>
          )
        }
        icon={<TotalUsersIcon />}
      />
      <StatisticCard
        title={t("dataUsage")}
        content={
          systemData &&
          formatBytes(
            systemData.incoming_bandwidth + systemData.outgoing_bandwidth
          )
        }
        icon={<NetworkIcon />}
      />
      <StatisticCard
        title={t("memoryUsage")}
        content={
          systemData && (
            <HStack alignItems="flex-end">
              <Text>{formatBytes(systemData.mem_used, 1, true)[0]}</Text>
              <Text
                fontWeight="normal"
                fontSize="lg"
                as="span"
                display="inline-block"
                pb="5px"
              >
                {formatBytes(systemData.mem_used, 1, true)[1]} /{" "}
                {formatBytes(systemData.mem_total, 1)}
              </Text>
            </HStack>
          )
        }
        icon={<MemoryIcon />}
      />
    </SimpleGrid>
  );
};
