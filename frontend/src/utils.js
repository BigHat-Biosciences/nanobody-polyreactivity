export const validateFastas = (fastas) => {
    if (!fastas) {
        return false;
    }
    fastas = fastas.trim();
    var lines = fastas.split('\n');

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex+=2) {
      if (lines[lineIndex][0] !== '>') {
        return false;
      }
      if (lineIndex+1 >= lines.length) {
        return false;
      }
      const sequence = lines[lineIndex+1].trim();
      if (!sequence) {
        return false;
      }
      if (!/^[ACDEFGHIKLMNPQRSTUVWY\s]+$/i.test(sequence)) {
        return false;
      }
    }
    return true;
}
