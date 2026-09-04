import { Box, HStack, Text, Tooltip } from "@chakra-ui/react";
import { FC } from "react";

type UserStatusProps = {
  lastOnline?: string | null;
};

const convertDateFormat = (lastOnline?: string | null): number | null => {
  if (!lastOnline) return null;

  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(lastOnline)
    ? lastOnline
    : `${lastOnline}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return null;
  return Math.floor(date.getTime() / 1000);
};

export const OnlineBadge: FC<UserStatusProps> = ({ lastOnline }) => {
  const currentTimeInSeconds = Math.floor(Date.now() / 1000);
  const unixTime = convertDateFormat(lastOnline);

  if (!lastOnline || unixTime === null) {
    return (
      <HStack spacing={1.5} flexShrink={0}>
        <Box border="1px solid" borderColor="gray.400" _dark={{ borderColor: "gray.600" }} className="circle" />
        <Text fontSize="2xs" color="gray.400">بدون فعالیت</Text>
      </HStack>
    );
  }

  const timeDifferenceInSeconds = Math.max(0, currentTimeInSeconds - unixTime);
  const exactTimestamp = new Date(unixTime * 1000).toLocaleString("fa-IR", {
    dateStyle: "medium",
    timeStyle: "medium",
  });

  if (timeDifferenceInSeconds <= 60) {
    return (
      <Tooltip label={`آخرین فعالیت: ${exactTimestamp}`} hasArrow>
        <HStack spacing={1.5} flexShrink={0}>
          <Box bg="green.300" _dark={{ bg: "green.500" }} className="circle pulse green" />
          <Text fontSize="2xs" color="green.300">الان آنلاین</Text>
        </HStack>
      </Tooltip>
    );
  }

  const relative = timeDifferenceInSeconds < 3600
    ? `${Math.floor(timeDifferenceInSeconds / 60).toLocaleString("fa-IR")} دقیقه پیش`
    : timeDifferenceInSeconds < 86400
      ? `${Math.floor(timeDifferenceInSeconds / 3600).toLocaleString("fa-IR")} ساعت پیش`
      : `${Math.floor(timeDifferenceInSeconds / 86400).toLocaleString("fa-IR")} روز پیش`;
  return (
    <Tooltip label={`آخرین فعالیت: ${exactTimestamp}`} hasArrow>
      <HStack spacing={1.5} flexShrink={0}>
        <Box bg="gray.400" _dark={{ bg: "gray.600" }} className="circle" />
        <Text fontSize="2xs" color="gray.400">آخرین فعالیت: {relative}</Text>
      </HStack>
    </Tooltip>
  );
};
