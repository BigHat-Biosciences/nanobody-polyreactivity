import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import { makeStyles } from '@mui/styles';

import { scoresUrl } from '../../routes';
import ResultsTable from '../../components/ResultsTable';
import vsLowThroughput from './allmodels_vs_lowthroughput.png';
import vsHighThroughput from './allmodels_vs_highthroughput.png';

const useStyles = makeStyles({
  heading: {
    paddingTop: '30px',
  },
  container: {
    maxWidth: '100%',
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  downloadButton: {
    textAlign: 'center',
    justifyContent: 'center',
    paddingTop: '2em',
  },
  img: {
    maxWidth: '100%',
    maxHeight: '100%',
  },
  table: {
    justifyContent: 'center',
    overflowX: 'scroll',
  },
});

export default function ResultsPage() {
  const classes = useStyles();
  const navigate = useNavigate();
  const { resultsId } = useParams();
  const [resultsIdValid, setResultsIdValid] = useState(true);
  const [resultsIdInput, setResultsIdInput] = useState('');
  const [resultsStr, setResultsStr] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getScoresForId = async () => {
      setLoading(true);
      setResultsIdValid(true);
      if (!resultsId) {
        setResultsIdValid(false);
        setLoading(false);
        return;
      }
      const scoreSequenceURLWithQuery = scoresUrl(resultsId);
      const fetchedResultBlob = await fetch(scoreSequenceURLWithQuery)
      .then((response) => {
        if (response.ok) {
          return response.blob();
        } else {
          alert('Your result ID is either invalid or your results are not ready yet.')
        }
      });
      if (!fetchedResultBlob) {
        setLoading(false);
        return;
      }
      const url = window.URL.createObjectURL(fetchedResultBlob);
      setDownloadUrl(url);
      const resultText = await fetchedResultBlob.text();
      setResultsStr(`${resultText}`);
      setLoading(false);
    }
    getScoresForId();
  }, [resultsId]);

  const showResults = () => {
    return (
      loading ?
      <Grid container style={{paddingTop: '2em'}} className={classes.centered}>
        <Grid item>
          <CircularProgress/>
        </Grid>
      </Grid> :
      <Grid container style={{paddingTop: '2em'}}>
        <Grid item className={classes.table} xs={12}>
          <ResultsTable resultsCSVStr={resultsStr}/>
        </Grid>
        <Grid item className={classes.downloadButton} xs={12}>
          {
            downloadUrl &&
            <Button
              variant="contained"
              href={downloadUrl}
              download={`${resultsId}.csv`}
            >
              Download Results
            </Button>
          }
        </Grid>
      </Grid>
    )
  };

  const showResultsSearchBar = () => {
    const retrieveResults = () => {
      navigate(`/results/${resultsIdInput}`)
    };
    return (
      <Grid container className={classes.centered} style={{paddingTop: '2em'}}>
        <Box
          component='form'
          sx={{
            '& > :not(style)': { m: 1, width: '30ch' },
          }}
          noValidate
        >
          <TextField
            id='standard-basic'
            label={'Input Results ID'}
            variant='standard'
            multiline
            onChange={(e) => setResultsIdInput(e.target.value)}
          />
          {
            resultsIdInput
            ?
            <Button
              variant='outlined'
              disableElevation
              onClick={retrieveResults}
            >
              Retrieve Results
            </Button>
            :
            <Button
              variant='outlined'
              disabled
            >
              Retrieve Results
            </Button>
          }
        </Box>
      </Grid>
    )
  }

  return (
    <Container className={classes.container}>
      <Grid container style={{paddingTop: '2em', paddingBottom: '4em'}}>
        <Grid item xs={12} sm={12} md={5} lg={4} xl={4}>
          <Box className={classes.heading}>
            <h2>Results</h2>
          </Box>
        </Grid>
        {
          resultsId &&
          <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
            <span><b>Results ID:</b> {resultsId}</span>
            <p>
              <br/>
              Scroll down view figures to help contextualize your data.
              <br/>
              If you requested scores for all double mutants of your nanobody,
               this may take a few minutes!
            </p>
          </Grid>
        }
        {
          showResultsSearchBar()
        }
        {
          resultsIdValid &&
          showResults()
        }
        <Grid item xs={12} sm={12} md={12} lg={12} xl={12}
          className={classes.centered} style={{paddingTop: '4em'}}
        >
          <img
            src={vsHighThroughput}
            alt='Example histograms of all models vs high throughput.'
            className={classes.img}
          />
        </Grid>
        <Grid item xs={12} sm={12} md={12} lg={12} xl={12}
          className={classes.centered} style={{paddingTop: '4em'}}
        >
          <img
            src={vsLowThroughput}
            alt='Example histograms of all models vs low throughput.'
            className={classes.img}
          />
        </Grid>
      </Grid>
    </Container>
  );
}
